"""Ontology endpoints — governed vocabulary for the knowledge graph.

* ``GET  /ontology``                          — types, predicates and terms with status.
* ``GET  /ontology/terms?q=``                 — search the glossary.
* ``GET  /ontology/terms/{id_or_name}``       — one term with linked entities.
* ``POST /ontology/types|predicates|terms``   — propose / update an entry (editor).
* ``POST /ontology/terms/{id}/links``         — link entities to a term (editor).
* ``POST /ontology/{kind}/{ident}/certify``   — certify (admin).
* ``POST /ontology/{kind}/{ident}/deprecate`` — deprecate (admin).

Every write lands as ``proposed`` (or keeps its status) and is audited; only an
admin can certify. Certified types and predicates constrain extraction and are
what governed-mode queries rely on.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from studio_api.graphrag_engine import engine
from studio_api.models import EntityTypeRequest, PredicateRequest, TermLinkRequest, TermRequest
from studio_api.security import caller_actor
from veritasgraph import governance
from veritasgraph.ontology import Ontology, key

ontology_router = APIRouter(prefix="/ontology", tags=["ontology"])

_KIND = {"types": "type", "predicates": "predicate", "terms": "term"}


def _ontology() -> Ontology:
    if engine.ontology is None or engine.store is None:
        raise HTTPException(status_code=503, detail="The ontology store is not available.")
    return engine.ontology


def _audited(actor: str, action: str, fn: Callable[[], Dict[str, Any]], target_field: str = "id") -> Dict[str, Any]:
    onto = _ontology()
    result = fn()
    governance.record_audit(
        onto.store, actor, action, str(result.get(target_field) or result.get("name") or ""), {}
    )
    return result


async def _run(fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(fn)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Not found: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@ontology_router.get("")
async def get_ontology() -> dict:
    return await asyncio.to_thread(_ontology().snapshot)


@ontology_router.get("/terms")
async def search_terms(
    q: str = Query(default="", max_length=200), limit: int = Query(default=50, ge=1, le=500)
) -> dict:
    return {"terms": await asyncio.to_thread(_ontology().list_terms, q, limit)}


@ontology_router.get("/terms/{term}")
async def get_term(term: str) -> dict:
    found = await asyncio.to_thread(_ontology().get_term, term)
    if found is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return found


@ontology_router.post("/types")
async def upsert_type(payload: EntityTypeRequest, request: Request) -> dict:
    actor = caller_actor(request)
    onto = _ontology()
    return await _run(
        lambda: _audited(
            actor,
            "ontology.type.upsert",
            lambda: onto.upsert_type(
                payload.name,
                description=payload.description,
                parent=payload.parent,
                synonyms=payload.synonyms,
                owner_id=actor,
            ),
            "name",
        )
    )


@ontology_router.post("/predicates")
async def upsert_predicate(payload: PredicateRequest, request: Request) -> dict:
    actor = caller_actor(request)
    onto = _ontology()
    return await _run(
        lambda: _audited(
            actor,
            "ontology.predicate.upsert",
            lambda: onto.upsert_predicate(
                payload.name,
                description=payload.description,
                domain_type=payload.domain_type,
                range_type=payload.range_type,
                inverse=payload.inverse,
                synonyms=payload.synonyms,
                owner_id=actor,
            ),
            "name",
        )
    )


@ontology_router.post("/terms")
async def upsert_term(payload: TermRequest, request: Request) -> dict:
    actor = caller_actor(request)
    onto = _ontology()
    return await _run(
        lambda: _audited(
            actor,
            "ontology.term.upsert",
            lambda: onto.upsert_term(
                payload.name,
                definition=payload.definition,
                synonyms=payload.synonyms,
                entity_ids=payload.entity_ids,
                owner_id=actor,
            ),
        )
    )


@ontology_router.post("/terms/{term}/links")
async def link_term(term: str, payload: TermLinkRequest, request: Request) -> dict:
    actor = caller_actor(request)
    onto = _ontology()

    def _link() -> Dict[str, Any]:
        found = onto.get_term(term)
        if found is None:
            raise KeyError(term)
        return onto.link_entities(found["id"], payload.entity_ids)

    return await _run(lambda: _audited(actor, "ontology.term.link", _link))


async def _set_status(kind: str, ident: str, status: str, request: Request) -> dict:
    actor = caller_actor(request)
    onto = _ontology()
    singular = _KIND[kind]

    def _do() -> Dict[str, Any]:
        target = ident
        if singular == "term":
            found = onto.get_term(ident)
            if found is None:
                raise KeyError(ident)
            target = found["id"]
        elif singular == "predicate":
            target = key(ident).replace(" ", "_")  # matches Ontology.upsert_predicate
        else:
            target = key(ident)
        return onto.set_status(singular, target, status)

    action = f"ontology.{singular}.{'certify' if status == 'certified' else 'deprecate'}"
    return await _run(lambda: _audited(actor, action, _do, "id" if singular == "term" else "name"))


@ontology_router.post("/{kind}/{ident}/certify")
async def certify(kind: Literal["types", "predicates", "terms"], ident: str, request: Request) -> dict:
    return await _set_status(kind, ident, "certified", request)


@ontology_router.post("/{kind}/{ident}/deprecate")
async def deprecate(kind: Literal["types", "predicates", "terms"], ident: str, request: Request) -> dict:
    return await _set_status(kind, ident, "deprecated", request)
