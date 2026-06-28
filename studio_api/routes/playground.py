"""Agent playground: run a stored agent against its local Ollama model.

This lets the studio UI actually *test* an agent rather than just configure it.
A chat request names an agent, the route loads that agent's model (its ``kind``)
and system instructions (``config.prompt`` or ``description``), then forwards the
conversation to the local Ollama daemon's ``/api/chat`` endpoint.

If Ollama is unreachable the route returns HTTP 503 with a clear message so the
UI can surface the problem instead of hanging.
"""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, HTTPException

from studio_api.dependencies import get_store
from studio_api.models import PlaygroundChatRequest
from studio_api.orchestrator import Orchestrator
from studio_api.store import StudioStore

playground_router = APIRouter(prefix="/playground", tags=["playground"])


def _ollama_base() -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    if not host.startswith("http"):
        host = f"http://{host}"
    return host.rstrip("/")


@playground_router.post("/chat")
async def chat(
    payload: PlaygroundChatRequest, store: StudioStore = Depends(get_store)
) -> dict:
    agent = store.get_resource("agents", payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    model = agent.kind
    if not model:
        raise HTTPException(
            status_code=400,
            detail="Agent has no model assigned (kind is empty).",
        )

    # Run the studio orchestration pipeline (guardrails -> memory -> graph ->
    # headroom budget -> tools). This builds the message buffer and a trace.
    orchestrator = Orchestrator(store)
    history = [{"role": t.role, "content": t.content} for t in payload.history]
    prepared = orchestrator.prepare(agent, payload.message, history)

    # Input guardrails can short-circuit the run before any model call.
    if prepared["blocked"]:
        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "model": model,
            "reply": prepared["block_reason"],
            "blocked": True,
            "eval_count": 0,
            "total_duration": 0,
            "trace": prepared["trace"],
            "citations": [],
            "reasoning_path": [],
            "subgraph": {"nodes": [], "edges": []},
        }

    body = {"model": model, "messages": prepared["messages"], "stream": False}
    url = f"{_ollama_base()}/api/chat"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        if exc.response.status_code == 404:
            detail = (
                f"Model '{model}' is not available in Ollama. "
                f"Pull it first: ollama pull {model}"
            )
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.HTTPError as exc:  # connection refused, timeout, etc.
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not reach the local Ollama runtime at "
                f"{_ollama_base()}. Is `ollama serve` running?"
            ),
        ) from exc

    raw_reply = (result.get("message") or {}).get("content", "")
    # Output guardrails + memory persistence + data logging.
    final = orchestrator.finalize(
        agent, prepared["user_text"], raw_reply, prepared["trace"]
    )

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "model": model,
        "reply": final["reply"],
        "blocked": False,
        "eval_count": result.get("eval_count"),
        "total_duration": result.get("total_duration"),
        "trace": final["trace"],
        "citations": prepared["citations"],
        "reasoning_path": prepared["reasoning_path"],
        "subgraph": prepared["subgraph"],
    }


@playground_router.get("/agents/{agent_id}/memory")
async def get_memory(agent_id: str, store: StudioStore = Depends(get_store)) -> dict:
    agent = store.get_resource("agents", agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "turns": store.get_memory(agent_id, limit=50)}


@playground_router.delete("/agents/{agent_id}/memory")
async def clear_memory(agent_id: str, store: StudioStore = Depends(get_store)) -> dict:
    agent = store.get_resource("agents", agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    store.clear_memory(agent_id)
    return {"message": "Memory cleared", "agent_id": agent_id}


@playground_router.get("/agents/{agent_id}/data")
async def get_data(agent_id: str, store: StudioStore = Depends(get_store)) -> dict:
    agent = store.get_resource("agents", agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "interactions": store.get_interactions(agent_id, limit=20)}

