"""FastAPI backend for the Municipality Incident Reporting Chatbot.

Exposes the :class:`app.orchestrator.IncidentChatbot` over HTTP so the Next.js
UI (in ``web/``) can drive the full VeritasGraph-backed pipeline.

Endpoints
---------
* ``GET  /api/health``  — liveness + graph stats.
* ``POST /api/report``  — submit a complaint (multipart: text, zone,
  location_text, lat, lon, name, phone, email, optional photo file). Returns
  the bot reply, outcome, score and case id.
* ``GET  /api/cases``   — list registered cases.
* ``GET  /api/graph``   — the municipal knowledge graph (nodes/edges/stats).

Run:
    uvicorn api:app --host 127.0.0.1 --port 8899
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app import IncidentChatbot

app = FastAPI(title="Municipality Incident Reporting Chatbot API", version="1.0.0")

# Allow the Next.js dev server (and same-origin proxy) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# One shared chatbot (and thus one VeritasGraph engine) for the process.
bot = IncidentChatbot()

# Uploaded photos are written here so the CV backend can read them. The
# simulated backend infers detections from the file name (offline); a real
# YOLO/VLM backend would read the pixels.
_UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="muni-uploads-"))


@app.get("/api/health")
def health() -> dict:
    stats = bot.kg.engine.graph().get("stats", {})
    return {"status": "ok", "graph": stats}


@app.post("/api/report")
async def report(
    text: str = Form(...),
    zone: Optional[str] = Form(None),
    location_text: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
) -> dict:
    image_path: Optional[str] = None
    photo_name: Optional[str] = None
    if photo is not None and photo.filename:
        # Preserve the original file name so the offline CV backend can infer
        # the depicted object (e.g. "garbage_overflow.jpg").
        safe_name = Path(photo.filename).name
        # Recreate the upload dir defensively — it lives under /tmp and may be
        # wiped by cleanup between requests.
        _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        dest = _UPLOAD_DIR / safe_name
        with dest.open("wb") as fh:
            shutil.copyfileobj(photo.file, fh)
        image_path = str(dest)
        photo_name = safe_name

    location = {}
    if zone:
        location["zone"] = zone.strip().lower()
    if location_text and location_text.strip():
        location["text"] = location_text.strip()
    if lat is not None:
        location["lat"] = lat
    if lon is not None:
        location["lon"] = lon

    reporter = {
        "name": (name or "").strip() or None,
        "phone": (phone or "").strip() or None,
        "email": (email or "").strip() or None,
    }

    result = bot.handle_report(
        text,
        image_path=image_path,
        location=(location or None),
        reporter=reporter,
    )
    payload = result.as_dict()
    payload["photo_name"] = photo_name
    return payload


@app.get("/api/cases")
def cases() -> dict:
    return {"cases": bot.cases.all()}


@app.get("/api/graph")
def graph() -> dict:
    return bot.kg.engine.graph()


@app.post("/api/reset")
def reset() -> dict:
    """Clear all registered cases (demo/E2E helper so runs are isolated)."""
    bot.cases.clear()
    return {"status": "reset", "cases": 0}
