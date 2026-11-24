"""Structured-data endpoints (``/structured``).

The router imports the structured package lazily, so Studio still starts
without the ``structured`` extra; the endpoints then answer 503.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from studio_api.models import (
    ConnectionCreate, FieldRoleUpdate, MeasureRequest, RelationshipCreate, StructuredAskRequest,
    StructuredSearchRequest, StructuredTermRequest,
)
from studio_api.security import caller_actor, caller_role

structured_router = APIRouter(prefix="/structured", tags=["structured"])
Kind = Literal["terms", "relationships", "measures"]
Action = Literal["accept", "certify", "reject", "deprecate"]


def _svc():
    try:
        from veritasgraph.structured import service
    except ImportError as exc:
        raise HTTPException(503, "Structured layer not installed: pip install 'veritasgraph-mcp[structured]'") from exc
    if not service.enabled():
        raise HTTPException(503, "Structured layer disabled: set VG_STRUCTURED_DSN.")
    return service


async def _call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    from veritasgraph.structured import errors

    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except errors.NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except errors.Conflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except errors.Invalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except errors.IndexMismatch as exc:
        raise HTTPException(409, str(exc)) from exc


@structured_router.get("/status")
async def status():
    return await _call(_svc().status)


# ---------------------------------------------------------------- connections
@structured_router.get("/connections")
async def list_connections():
    return {"items": await _call(_svc().list_connections)}


@structured_router.post("/connections", status_code=201)
async def create_connection(body: ConnectionCreate, request: Request):
    return await _call(_svc().create_connection, body.name, body.dsn, body.options.model_dump(), caller_actor(request))


@structured_router.delete("/connections/{conn_id}", status_code=204)
async def delete_connection(conn_id: str, request: Request):
    await _call(_svc().delete_connection, conn_id, caller_actor(request))
    return Response(status_code=204)


@structured_router.post("/connections/{conn_id}/test")
async def test_connection(conn_id: str):
    return await _call(_svc().test_connection, conn_id)


@structured_router.post("/connections/{conn_id}/sync", status_code=202)
async def sync_connection(conn_id: str, request: Request):
    return await _call(_svc().request_job, "sync", caller_actor(request), conn_id)


@structured_router.post("/connections/{conn_id}/compile", status_code=202)
async def compile_connection(conn_id: str, request: Request):
    return await _call(_svc().request_job, "compile", caller_actor(request), conn_id)


@structured_router.post("/reindex", status_code=202)
async def reindex(request: Request):
    return await _call(_svc().request_job, "reindex", caller_actor(request))


@structured_router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    return await _call(_svc().get_job, job_id)


# ---------------------------------------------------------------- catalog
@structured_router.get("/datasets")
async def list_datasets(connection_id: Optional[str] = Query(default=None, max_length=32)):
    return {"items": await _call(_svc().list_datasets, connection_id)}


@structured_router.get("/datasets/{ds_id}")
async def get_dataset(ds_id: str, request: Request):
    return await _call(_svc().get_dataset, ds_id, caller_role(request))


@structured_router.patch("/fields/{field_id}")
async def set_field_role(field_id: str, body: FieldRoleUpdate, request: Request):
    return await _call(_svc().set_field_role, field_id, body.role, caller_actor(request))


# ---------------------------------------------------------------- semantic objects
@structured_router.get("/{kind}")
async def list_objects(kind: Kind, status: Optional[str] = Query(default=None, max_length=16)):
    return {"items": await _call(_svc().list_objects, kind, status)}


@structured_router.post("/terms", status_code=201)
async def create_term(body: StructuredTermRequest, request: Request):
    return await _call(_svc().upsert_term, actor=caller_actor(request), **body.model_dump())


@structured_router.put("/terms/{term_id}")
async def update_term(term_id: str, body: StructuredTermRequest, request: Request):
    return await _call(_svc().upsert_term, actor=caller_actor(request), term_id=term_id, **body.model_dump())


@structured_router.post("/relationships", status_code=201)
async def create_relationship(body: RelationshipCreate, request: Request):
    return await _call(_svc().create_relationship, body.from_field_id, body.to_field_id, caller_actor(request))


@structured_router.post("/measures", status_code=201)
async def create_measure(body: MeasureRequest, request: Request):
    return await _call(_svc().upsert_measure, actor=caller_actor(request), **body.model_dump())


@structured_router.put("/measures/{measure_id}")
async def update_measure(measure_id: str, body: MeasureRequest, request: Request):
    return await _call(_svc().upsert_measure, actor=caller_actor(request), measure_id=measure_id, **body.model_dump())


@structured_router.post("/{kind}/{obj_id}/{action}")
async def transition(kind: Kind, obj_id: str, action: Action, request: Request):
    return await _call(_svc().transition, kind, obj_id, action, caller_actor(request))


# ---------------------------------------------------------------- search / ask
@structured_router.post("/search")
async def search(body: StructuredSearchRequest):
    return {"items": await _call(_svc().search, body.query, list(body.kinds), body.k)}


@structured_router.post("/ask")
async def ask(body: StructuredAskRequest, request: Request):
    return await _call(_svc().ask, body.question, actor=caller_actor(request), role=caller_role(request),
                       mode=body.mode, connection_id=body.connection_id)


@structured_router.get("/answers/{answer_id}")
async def get_answer(answer_id: str):
    return await _call(_svc().get_answer, answer_id)
