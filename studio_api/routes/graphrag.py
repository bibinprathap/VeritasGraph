"""GraphRAG endpoints — VeritasGraph knowledge graph features.

Exposes the :class:`studio_api.graphrag_engine.GraphRAGEngine` over HTTP:

* ``POST /graphrag/ingest``              — build/extend the graph from a document.
* ``GET  /graphrag/graph``               — nodes/edges for visualisation.
* ``POST /graphrag/import`` / ``GET /graphrag/export`` — round-trip a graph.
* ``DELETE /graphrag/graph``             — clear the graph (admin; snapshotted first).
* ``POST /graphrag/query``               — grounded multi-hop answer with strict citations;
  ``mode=governed`` requires certified terms and withholds ungrounded answers.
* ``POST /graphrag/answerable``          — can the graph answer this? (no LLM call)
* ``GET  /graphrag/answers/{id}``        — answer receipt; ``POST .../feedback`` rates it.
* ``GET/POST /graphrag/snapshots``, ``POST /graphrag/snapshots/{id}/restore`` (admin).
* ``GET  /graphrag/audit``, ``GET /graphrag/audit/verify`` — hash-chained audit trail.
* ``GET  /graphrag/entities/{id}``, ``POST /graphrag/entities/merge`` — curation.
* ``POST /graphrag/compile``, ``GET /graphrag/compile/runs``, ``GET /graphrag/compile/status``.
* ``GET  /graphrag/suggestions``, ``POST /graphrag/suggestions/{id}/accept|reject``.

LLM work runs in a worker thread so the event loop is never blocked, and Ollama
failures surface as clear 5xx responses. Text from PII-flagged sources is
redacted for roles below ``VERITASGRAPH_PII_REVEAL_ROLE``.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from studio_api.graphrag_engine import engine
from studio_api.models import (
    AnswerableRequest,
    FeedbackRequest,
    GraphImportRequest,
    GraphIngestRequest,
    GraphQueryRequest,
    MergeEntitiesRequest,
    SnapshotRequest,
)
from studio_api.security import caller_actor, caller_role
from veritasgraph import compile as compiler
from veritasgraph import governance, pii
from veritasgraph.answerability import check_answerable

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


def _store():
    if engine.store is None:
        raise HTTPException(status_code=503, detail="The graph store is not available.")
    return engine.store


# --------------------------------------------------------------------------- #
# Graph lifecycle
# --------------------------------------------------------------------------- #
@graphrag_router.post("/ingest")
async def ingest(payload: GraphIngestRequest, request: Request) -> dict:
    try:
        result = await asyncio.to_thread(
            engine.ingest, payload.title, payload.text, payload.model, actor=caller_actor(request)
        )
    except ValueError as exc:  # includes pii.PIIRejected
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - translate to a clean HTTP error
        raise _ollama_error(exc) from exc
    return {"message": "Document ingested", "result": result}


@graphrag_router.get("/graph")
async def get_graph(request: Request) -> dict:
    data = await asyncio.to_thread(engine.graph)
    return pii.redact_payload(data, caller_role(request))


@graphrag_router.post("/import")
async def import_graph(payload: GraphImportRequest, request: Request) -> dict:
    """Upload a pre-built knowledge graph (Graphify, Understand-Anything, AI Atlas, generic)."""
    try:
        result = await asyncio.to_thread(
            engine.import_graph,
            payload.graph,
            fmt=payload.format,
            source_type=payload.source_type,
            merge_strategy=payload.merge_strategy,
            title=payload.title,
            origin_version=payload.origin_version,
            actor=caller_actor(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - translate to a clean HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"message": "Graph imported", "result": result}


@graphrag_router.get("/export")
async def export_graph(request: Request) -> dict:
    """Export the full knowledge graph (sources, entities, relationships) for round-trip."""
    data = await asyncio.to_thread(engine.export_graph)
    return pii.redact_payload(data, caller_role(request))


@graphrag_router.delete("/graph")
async def clear_graph(request: Request) -> dict:
    result = await asyncio.to_thread(engine.clear, actor=caller_actor(request))
    return {"message": "Knowledge graph cleared", **(result or {})}


# --------------------------------------------------------------------------- #
# Questions and answers
# --------------------------------------------------------------------------- #
@graphrag_router.post("/query")
async def query(payload: GraphQueryRequest, request: Request) -> dict:
    try:
        result = await asyncio.to_thread(
            engine.query,
            payload.question,
            payload.model,
            payload.max_depth,
            payload.max_nodes,
            mode=payload.mode,
            actor=caller_actor(request),
        )
    except Exception as exc:  # noqa: BLE001 - translate to a clean HTTP error
        raise _ollama_error(exc) from exc
    return pii.redact_answer_payload(result, caller_role(request))


@graphrag_router.post("/answerable")
async def answerable(payload: AnswerableRequest) -> dict:
    """Report whether the graph covers the question — no LLM call, no answer."""
    return await asyncio.to_thread(check_answerable, engine, payload.question, payload.mode)


@graphrag_router.get("/answers/{answer_id}")
async def get_answer(answer_id: str, request: Request) -> dict:
    answer = await asyncio.to_thread(governance.get_answer, _store(), answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    return pii.redact_answer_payload(answer, caller_role(request))


@graphrag_router.post("/answers/{answer_id}/feedback")
async def answer_feedback(answer_id: str, payload: FeedbackRequest, request: Request) -> dict:
    try:
        return await asyncio.to_thread(
            governance.add_feedback,
            _store(),
            answer_id,
            payload.rating,
            payload.comment,
            caller_actor(request),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Answer not found") from exc


# --------------------------------------------------------------------------- #
# Snapshots and audit
# --------------------------------------------------------------------------- #
@graphrag_router.get("/snapshots")
async def list_snapshots() -> dict:
    return {"snapshots": await asyncio.to_thread(governance.list_snapshots, _store())}


@graphrag_router.post("/snapshots")
async def create_snapshot(payload: SnapshotRequest, request: Request) -> dict:
    try:
        return await asyncio.to_thread(engine.snapshot, payload.label, actor=caller_actor(request))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@graphrag_router.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str, request: Request) -> dict:
    try:
        return await asyncio.to_thread(engine.restore, snapshot_id, actor=caller_actor(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Snapshot not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@graphrag_router.get("/audit")
async def list_audit(
    limit: int = Query(default=100, ge=1, le=1000), action: Optional[str] = None
) -> dict:
    return {"events": await asyncio.to_thread(governance.list_audit, _store(), limit, action)}


@graphrag_router.get("/audit/verify")
async def verify_audit() -> dict:
    return await asyncio.to_thread(governance.verify_audit, _store())


# --------------------------------------------------------------------------- #
# Curation
# --------------------------------------------------------------------------- #
@graphrag_router.get("/entities/{entity_id}")
async def get_entity(entity_id: str, request: Request) -> dict:
    ent = await asyncio.to_thread(engine.entity, entity_id)
    if ent is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return pii.redact_payload(ent, caller_role(request))


@graphrag_router.post("/entities/merge")
async def merge_entities(payload: MergeEntitiesRequest, request: Request) -> dict:
    try:
        return await asyncio.to_thread(
            engine.merge_entities, payload.keep_id, payload.drop_id, actor=caller_actor(request)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown entity {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Compile and suggestions
# --------------------------------------------------------------------------- #
@graphrag_router.post("/compile")
async def run_compile(request: Request) -> dict:
    _store()
    result = await asyncio.to_thread(
        compiler.run_compile, engine, trigger="manual", actor=caller_actor(request)
    )
    if result.get("status") == "busy":
        raise HTTPException(status_code=409, detail="A compile run is already in progress.")
    return result


@graphrag_router.get("/compile/runs")
async def compile_runs(limit: int = Query(default=20, ge=1, le=200)) -> dict:
    return {"runs": await asyncio.to_thread(compiler.list_runs, _store(), limit)}


@graphrag_router.get("/compile/status")
async def compile_status() -> dict:
    return await asyncio.to_thread(compiler.status, _store())


@graphrag_router.get("/suggestions")
async def list_suggestions(
    request: Request,
    status: str = Query(default="open", pattern="^(open|accepted|rejected)$"),
    kind: Optional[str] = Query(default=None, pattern="^(merge|term|violation|orphan)$"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict:
    items = await asyncio.to_thread(compiler.list_suggestions, _store(), status, kind, limit)
    return {"suggestions": pii.redact_payload(items, caller_role(request))}


async def _resolve(suggestion_id: str, accept: bool, request: Request) -> dict:
    _store()
    try:
        return await asyncio.to_thread(
            compiler.resolve_suggestion, engine, suggestion_id, accept, caller_actor(request)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Suggestion not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@graphrag_router.post("/suggestions/{suggestion_id}/accept")
async def accept_suggestion(suggestion_id: str, request: Request) -> dict:
    return await _resolve(suggestion_id, True, request)


@graphrag_router.post("/suggestions/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: str, request: Request) -> dict:
    return await _resolve(suggestion_id, False, request)
