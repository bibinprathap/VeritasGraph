"""FastAPI HTTP wrapper around the floorplan-kg extraction engine.

Thin transport layer only: request validation, temp-file handling and JSON
serialisation. Every line of extraction logic stays in ``engine/pipeline.py``,
which is imported in place from the parent repository — never copied.
"""

from __future__ import annotations

import logging
import math
import re
import shutil
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

# ``engine/`` lives one directory above ``backend/``; put the repository root on
# ``sys.path`` so the engine is imported rather than duplicated.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.pipeline import process  # noqa: E402  (sys.path bootstrap must run first)

logger = logging.getLogger("floorbackend")

# Matches the frontend's ``MAX_UPLOAD_BYTES`` in web/src/app/api/process/route.ts.
MAX_UPLOAD_BYTES = 80 * 1024 * 1024
_MULTIPART_OVERHEAD = 1024 * 1024
_CHUNK_BYTES = 1 << 20
_ALLOWED_METHODS = ("pymupdf", "pdfplumber")
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_ABS_PATH = re.compile(r"(?:[A-Za-z]:)?(?:/[\w.\-]+)+")

# The engine is CPU and memory heavy and this host is shared: exactly one PDF
# is extracted at a time. No multiprocessing, no worker fan-out, no queue.
_process_lock = threading.Lock()

app = FastAPI(title="floorbackend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pmspace.ai",
        "https://www.pmspace.ai",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# error surface — uniform ``{"error": ...}``, never a traceback, never a path
# --------------------------------------------------------------------------

def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


# Routing raises Starlette's own HTTPException; cover both so every error is
# the same ``{"error": ...}`` shape.
@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return _error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def _request_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        if "file" in [str(part) for part in error.get("loc", ())]:
            return _error(400, "A PDF file is required in the 'file' field.")
    return _error(400, "Invalid request.")


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error while serving %s", request.url.path)
    return _error(500, "Internal server error.")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _safe_message(exc: BaseException) -> str:
    """Last meaningful line of an engine failure, path-free and truncated."""
    lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
    message = lines[-1] if lines else type(exc).__name__
    message = _ABS_PATH.sub("<path>", message).strip()
    if not message:
        message = "the PDF could not be parsed"
    if len(message) > 300:
        message = message[:300] + "…"
    return f"Error processing PDF: {message}"


def _is_pdf(filename: Optional[str]) -> bool:
    return bool(filename) and filename.lower().endswith(".pdf")


def _temp_basename(filename: str) -> str:
    """Directory-component-free, filesystem-safe name that still ends in .pdf."""
    base = _SAFE_CHARS.sub("_", Path(filename).name)
    if not base or base in {".", ".."}:
        base = "upload.pdf"
    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"
    return base


def _parse_ceiling(raw: Optional[str]) -> Optional[float]:
    if raw is None or not str(raw).strip():
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        raise HTTPException(400, "ceilingHeightFeet must be a number.") from None
    if not math.isfinite(value) or value <= 0:
        raise HTTPException(
            400, "ceilingHeightFeet must be a positive, finite number."
        ) from None
    return value


def _run_engine(path: str, method: str, assumptions: Optional[dict]) -> dict:
    with _process_lock:
        return process(path, backend=method, assumptions=assumptions)


async def _spool(upload: UploadFile, dest: Path) -> int:
    """Stream the upload to disk, aborting as soon as the size limit is passed."""
    total = 0
    with dest.open("wb") as handle:
        while True:
            chunk = await upload.read(_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    413,
                    f"File is larger than the {MAX_UPLOAD_BYTES // 1024 // 1024} MB limit.",
                )
            handle.write(chunk)
    return total


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "floorbackend"}


@app.post("/process")
async def process_pdf(
    request: Request,
    file: UploadFile = File(...),
    method: str = Form("pymupdf"),
    ceilingHeightFeet: Optional[str] = Form(None),
) -> dict:
    # Cheap pre-flight: reject an oversized body before it is spooled to disk.
    content_length = request.headers.get("content-length", "")
    if content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES + _MULTIPART_OVERHEAD:
        raise HTTPException(
            413,
            f"File is larger than the {MAX_UPLOAD_BYTES // 1024 // 1024} MB limit.",
        )

    if method not in _ALLOWED_METHODS:
        raise HTTPException(
            400,
            f"Unsupported method {method!r}. Allowed methods: pymupdf, pdfplumber.",
        )

    if not _is_pdf(file.filename):
        raise HTTPException(415, "Only .pdf files are accepted.")

    ceiling = _parse_ceiling(ceilingHeightFeet)

    tmp_dir = Path(tempfile.mkdtemp(prefix="floorbackend-"))
    try:
        dest = tmp_dir / _temp_basename(file.filename or "")
        size = await _spool(file, dest)

        if size == 0:
            raise HTTPException(
                422, "Error processing PDF: the uploaded file is empty (0 bytes)."
            )
        with dest.open("rb") as handle:
            header = handle.read(8)
        if not header.startswith(b"%PDF-"):
            raise HTTPException(415, "The uploaded file is not a valid PDF.")

        assumptions = {"ceilingHeightFeet": ceiling} if ceiling is not None else None

        try:
            result = await run_in_threadpool(_run_engine, str(dest), method, assumptions)
        except HTTPException:
            raise
        except Exception as exc:  # engine/parser failure — controlled message only
            logger.exception("engine failed while processing %s", dest.name)
            raise HTTPException(422, _safe_message(exc)) from None

        return result
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
