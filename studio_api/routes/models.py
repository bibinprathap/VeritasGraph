"""Discovery endpoint for locally available LLM models.

The studio agent builder previously hard-coded placeholder model names. This
router reports the models that are actually installed on the host so the UI can
populate the model picker with real choices.

Discovery order:

1. Query the local Ollama daemon HTTP API (``OLLAMA_HOST`` or
   ``http://127.0.0.1:11434/api/tags``).
2. Fall back to shelling out to ``ollama list`` if the HTTP API is unreachable.

If no models are found the endpoint returns an empty list so the UI can show a
clear "no local models" message instead of fake data.
"""

from __future__ import annotations

import os
import subprocess

import httpx
from fastapi import APIRouter

models_router = APIRouter(prefix="/models", tags=["models"])


def _ollama_base() -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    if not host.startswith("http"):
        host = f"http://{host}"
    return host.rstrip("/")


def _from_http() -> list[dict]:
    url = f"{_ollama_base()}/api/tags"
    resp = httpx.get(url, timeout=3.0)
    resp.raise_for_status()
    payload = resp.json()
    models: list[dict] = []
    for entry in payload.get("models", []):
        name = entry.get("name")
        if not name:
            continue
        models.append(
            {
                "id": name,
                "name": name,
                "size": entry.get("size"),
                "family": (entry.get("details") or {}).get("family"),
                "provider": "ollama",
            }
        )
    return models


def _from_cli() -> list[dict]:
    proc = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        timeout=5.0,
        check=True,
    )
    models: list[dict] = []
    lines = proc.stdout.strip().splitlines()
    for line in lines[1:]:  # skip header row
        name = line.split()[0] if line.split() else ""
        if name:
            models.append({"id": name, "name": name, "provider": "ollama"})
    return models


@models_router.get("/")
async def list_models() -> dict:
    """Return the LLM models available on this machine."""
    models: list[dict] = []
    source = "none"
    try:
        models = _from_http()
        source = "ollama-http"
    except Exception:  # noqa: BLE001 - fall back to CLI on any HTTP failure
        try:
            models = _from_cli()
            source = "ollama-cli"
        except Exception:  # noqa: BLE001 - no local runtime available
            models = []
            source = "none"
    return {"items": models, "count": len(models), "source": source}
