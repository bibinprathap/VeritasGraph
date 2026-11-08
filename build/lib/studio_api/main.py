"""FastAPI application for the Agent Studio backend.

Run with::

    uvicorn studio_api.main:app --reload --port 8200

The studio UI (``demos/agent-studio/index.html``) is served at ``/studio`` when
present, and the JSON API is mounted under the section prefixes.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from studio_api import __version__
from studio_api.graphrag_engine import engine
from studio_api.routes.evaluation import evaluation_router
from studio_api.routes.finetune import finetune_router
from studio_api.routes.graphrag import graphrag_router
from studio_api.routes.knowledge import knowledge_router
from studio_api.routes.mcp import mcp_router
from studio_api.routes.models import models_router
from studio_api.routes.ontology import ontology_router
from studio_api.routes.playground import playground_router
from studio_api.routes.resources import resource_routers
from studio_api.routes.tools import tools_router
from studio_api.routes.workspace import workspace_router
from studio_api.security import authorize, check_config
from veritasgraph import compile as compiler

_REPO_ROOT = Path(__file__).resolve().parent.parent
_STUDIO_UI = _REPO_ROOT / "demos" / "agent-studio" / "index.html"

check_config()

_log = logging.getLogger("studio_api")


async def _compile_loop(interval: int) -> None:
    """Run the compile pipeline every ``interval`` seconds (``busy`` runs are skipped)."""
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(compiler.run_compile, engine, trigger="schedule", actor="scheduler")
        except Exception:  # noqa: BLE001 - a failed run is recorded; keep scheduling
            _log.exception("Scheduled compile run failed")


@asynccontextmanager
async def _lifespan(_: FastAPI):
    interval = compiler.interval_seconds()
    task = (
        asyncio.create_task(_compile_loop(interval))
        if interval and engine.store is not None
        else None
    )
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="Agent Studio API", version=__version__, lifespan=_lifespan)

# The bundled UI is served same-origin from /studio and needs no CORS. Only list
# origins that genuinely host a separate front end.
_cors_origins = [
    o.strip() for o in os.environ.get("STUDIO_CORS_ORIGINS", "").split(",") if o.strip()
]
if "*" in _cors_origins:
    raise RuntimeError("STUDIO_CORS_ORIGINS must list explicit origins, not '*'")
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

# Every data route requires a bearer token; /health and the static UI shell stay
# public so the UI can load and then ask for a token.
_protected = [Depends(authorize)]

# Collection sections (agents, tools, knowledge, guardrails, memory, data).
for router in resource_routers:
    app.include_router(router, dependencies=_protected)

# Tool-specific actions (probe/test a real endpoint).
app.include_router(tools_router, dependencies=_protected)

# Extra section-specific routers.
app.include_router(knowledge_router, dependencies=_protected)
app.include_router(evaluation_router, dependencies=_protected)
app.include_router(finetune_router, dependencies=_protected)
app.include_router(workspace_router, dependencies=_protected)
app.include_router(models_router, dependencies=_protected)
app.include_router(playground_router, dependencies=_protected)
app.include_router(graphrag_router, dependencies=_protected)
app.include_router(ontology_router, dependencies=_protected)
app.include_router(mcp_router, dependencies=_protected)


@app.get("/health", tags=["meta"])
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "version": __version__})


@app.get("/ready", tags=["meta"])
async def ready() -> JSONResponse:
    """Readiness: the graph store answers a query. Public; reveals no graph content."""
    if engine.store is None:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    try:
        schema = await asyncio.to_thread(engine.store.schema_version)
    except Exception:  # noqa: BLE001 - any store failure means not ready
        _log.exception("Readiness check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ready", "schema_version": schema})


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/studio")


@app.get("/studio", include_in_schema=False)
async def studio_ui():
    if _STUDIO_UI.is_file():
        return FileResponse(str(_STUDIO_UI))
    return JSONResponse(
        status_code=404,
        content={"detail": "Studio UI not found", "expected": str(_STUDIO_UI)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8200)
