"""FastAPI application for the Agent Studio backend.

Run with::

    uvicorn studio_api.main:app --reload --port 8200

The studio UI (``demos/agent-studio/index.html``) is served at ``/studio`` when
present, and the JSON API is mounted under the section prefixes.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from studio_api import __version__
from studio_api.routes.evaluation import evaluation_router
from studio_api.routes.finetune import finetune_router
from studio_api.routes.graphrag import graphrag_router
from studio_api.routes.knowledge import knowledge_router
from studio_api.routes.models import models_router
from studio_api.routes.playground import playground_router
from studio_api.routes.resources import resource_routers
from studio_api.routes.workspace import workspace_router

_REPO_ROOT = Path(__file__).resolve().parent.parent
_STUDIO_UI = _REPO_ROOT / "demos" / "agent-studio" / "index.html"

app = FastAPI(title="Agent Studio API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Collection sections (agents, tools, knowledge, guardrails, memory, data).
for router in resource_routers:
    app.include_router(router)

# Extra section-specific routers.
app.include_router(knowledge_router)
app.include_router(evaluation_router)
app.include_router(finetune_router)
app.include_router(workspace_router)
app.include_router(models_router)
app.include_router(playground_router)
app.include_router(graphrag_router)


@app.get("/health", tags=["meta"])
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "version": __version__})


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
