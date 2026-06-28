"""GraphRAG endpoints — VeritasGraph knowledge graph features.

Exposes the :class:`studio_api.graphrag_engine.GraphRAGEngine` over HTTP:

* ``POST /graphrag/ingest``  — build/extend the knowledge graph from a document.
* ``GET  /graphrag/graph``   — fetch nodes/edges for visualisation.
* ``POST /graphrag/query``   — graph-grounded multi-hop answer with citations.
* ``DELETE /graphrag/graph`` — clear the graph.

LLM work runs in a worker thread so the event loop is never blocked, and Ollama
failures surface as clear 5xx responses.
"""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, HTTPException

from studio_api.graphrag_engine import engine
from studio_api.models import GraphIngestRequest, GraphQueryRequest

graphrag_router = APIRouter(prefix="/graphrag", tags=["graphrag"])


def _ollama_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return HTTPException(
            status_code=502,
            detail="The selected model is not available in Ollama. Pull it first.",
        )
    if isinstance(exc, httpx.HTTPError):
        return HTTPException(
            status_code=503,
            detail="Could not reach the local Ollama runtime. Is `ollama serve` running?",
        )
    return HTTPException(status_code=500, detail=str(exc))


@graphrag_router.post("/ingest")
async def ingest(payload: GraphIngestRequest) -> dict:
    try:
        result = await asyncio.to_thread(
            engine.ingest, payload.title, payload.text, payload.model
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - translate to a clean HTTP error
        raise _ollama_error(exc) from exc
    return {"message": "Document ingested", "result": result}


@graphrag_router.get("/graph")
async def get_graph() -> dict:
    return await asyncio.to_thread(engine.graph)


@graphrag_router.delete("/graph")
async def clear_graph() -> dict:
    await asyncio.to_thread(engine.clear)
    return {"message": "Knowledge graph cleared"}


@graphrag_router.post("/query")
async def query(payload: GraphQueryRequest) -> dict:
    try:
        result = await asyncio.to_thread(
            engine.query,
            payload.question,
            payload.model,
            payload.max_depth,
            payload.max_nodes,
        )
    except Exception as exc:  # noqa: BLE001 - translate to a clean HTTP error
        raise _ollama_error(exc) from exc
    return result
