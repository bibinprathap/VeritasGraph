from __future__ import annotations

from typing import Any, Dict, List, Optional

import sqlalchemy as sa

from veritasgraph.llm import Embedder, endpoint, rerank_mode
from veritasgraph.structured import ask as _ask
from veritasgraph.structured import config, measures, secrets, worker
from veritasgraph.structured.config import enabled  # re-export
from veritasgraph.structured.connectors import Source, check_dsn
from veritasgraph.structured.errors import Conflict, Invalid, NotFound
from veritasgraph.structured.search import KINDS, search as _search
from veritasgraph.structured.store import db
from veritasgraph.structured.store import schema as t

_TRANSITIONS = {
    "accept": ({"proposed"}, "accepted"),
    "certify": ({"accepted"}, "certified"),
    "reject": ({"proposed", "accepted"}, "rejected"),
    "deprecate": ({"accepted", "certified"}, "deprecated"),
}
_TABLES = {"terms": t.term, "relationships": t.relationship, "measures": t.measure}


def _row(r) -> Dict[str, Any]:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r._mapping.items()}


# ---------------------------------------------------------------- connections
def list_connections() -> List[Dict[str, Any]]:
    cols = [c for c in t.connection.c if c.name != "dsn_encrypted"]
    with db.tx() as conn:
        return [_row(r) for r in conn.execute(sa.select(*cols).order_by(t.connection.c.name))]


def create_connection(name: str, dsn: str, options: Dict[str, Any], actor: str) -> Dict[str, Any]:
    dialect = check_dsn(dsn)
    Source(dsn).test()
    conn_id = db.new_id("conn")
    values = dict(id=conn_id, name=name, dialect=dialect.name, dsn_encrypted=secrets.seal(dsn),
                  dsn_display=secrets.display_dsn(dsn), options=options, owner=actor)
    with db.tx() as conn:
        if conn.execute(sa.select(t.connection.c.id).where(t.connection.c.name == name)).first():
            raise Conflict(f"A connection named '{name}' already exists.")
        conn.execute(sa.insert(t.connection).values(**values))
        db.audit(conn, actor, "create", "connection", conn_id, after={"name": name, "dialect": dialect.name})
    return {k: v for k, v in values.items() if k != "dsn_encrypted"}


def delete_connection(conn_id: str, actor: str) -> None:
    with db.tx() as conn:
        ids = [r[0] for r in conn.execute(sa.select(t.dataset.c.id).where(t.dataset.c.connection_id == conn_id))]
        fids = [r[0] for r in conn.execute(sa.select(t.field.c.id).where(t.field.c.dataset_id.in_(ids)))] if ids else []
        conn.execute(sa.delete(t.embedding).where(t.embedding.c.object_id.in_(ids + fids)))
        if not conn.execute(sa.delete(t.connection).where(t.connection.c.id == conn_id)).rowcount:
            raise NotFound(f"connection {conn_id} not found")
        db.audit(conn, actor, "delete", "connection", conn_id)


def test_connection(conn_id: str) -> Dict[str, Any]:
    from veritasgraph.structured.catalog import open_source

    _, src = open_source(conn_id)
    src.test()
    return {"ok": True}


def request_job(kind: str, actor: str, connection_id: Optional[str] = None) -> Dict[str, Any]:
    if kind in ("sync", "compile"):
        with db.tx() as conn:
            if not conn.execute(sa.select(t.connection.c.id).where(t.connection.c.id == connection_id)).first():
                raise NotFound(f"connection {connection_id} not found")
    return {"job_id": worker.enqueue(kind, actor, connection_id)}


def get_job(job_id: str) -> Dict[str, Any]:
    with db.tx() as conn:
        r = conn.execute(sa.select(t.job).where(t.job.c.id == job_id)).first()
    if r is None:
        raise NotFound(f"job {job_id} not found")
    return _row(r)


# ---------------------------------------------------------------- catalog
def list_datasets(connection_id: Optional[str] = None) -> List[Dict[str, Any]]:
    stmt = sa.select(t.dataset).order_by(t.dataset.c.schema_name, t.dataset.c.name)
    if connection_id:
        stmt = stmt.where(t.dataset.c.connection_id == connection_id)
    with db.tx() as conn:
        return [_row(r) for r in conn.execute(stmt)]


def get_dataset(ds_id: str, role: str) -> Dict[str, Any]:
    from veritasgraph import pii

    with db.tx() as conn:
        d = conn.execute(sa.select(t.dataset).where(t.dataset.c.id == ds_id)).first()
        if d is None:
            raise NotFound(f"dataset {ds_id} not found")
        fields = [_row(f) for f in conn.execute(sa.select(t.field).where(t.field.c.dataset_id == ds_id).order_by(t.field.c.ordinal))]
    if not pii.can_see_pii(role):
        for f in fields:
            if f["pii_class"]:
                f["sample"] = []
    return {**_row(d), "fields": fields}


def set_field_role(field_id: str, role_name: str, actor: str) -> Dict[str, Any]:
    if role_name not in t.ROLES:
        raise Invalid(f"role must be one of {t.ROLES}")
    with db.tx() as conn:
        if not conn.execute(sa.update(t.field).where(t.field.c.id == field_id)
                            .values(role=role_name, role_origin="manual")).rowcount:
            raise NotFound(f"field {field_id} not found")
        db.audit(conn, actor, "set_role", "field", field_id, after={"role": role_name})
    return {"id": field_id, "role": role_name}


# ---------------------------------------------------------------- semantic objects
def list_objects(kind: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    table = _TABLES[kind]
    stmt = sa.select(table)
    if status:
        stmt = stmt.where(table.c.status == status)
    with db.tx() as conn:
        return [_row(r) for r in conn.execute(stmt.order_by(table.c.created_at.desc()))]


def transition(kind: str, obj_id: str, action: str, actor: str) -> Dict[str, Any]:
    allowed_from, target = _TRANSITIONS[action]
    table = _TABLES[kind]
    with db.tx() as conn:
        row = conn.execute(sa.select(table.c.status).where(table.c.id == obj_id).with_for_update()).first()
        if row is None:
            raise NotFound(f"{kind[:-1]} {obj_id} not found")
        if row.status not in allowed_from:
            raise Conflict(f"Cannot {action} a {row.status} {kind[:-1]}.")
        conn.execute(sa.update(table).where(table.c.id == obj_id).values(status=target, updated_at=sa.func.now()))
        db.audit(conn, actor, action, kind[:-1], obj_id, before={"status": row.status}, after={"status": target})
    return {"id": obj_id, "status": target}


def upsert_term(*, name: str, definition: str, synonyms: List[str], dataset_ids: List[str], actor: str,
                term_id: Optional[str] = None) -> Dict[str, Any]:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    with db.tx() as conn:
        if term_id is None:
            if conn.execute(sa.select(t.term.c.id).where(sa.func.lower(t.term.c.name) == name.lower())).first():
                raise Conflict(f"A term named '{name}' already exists.")
            term_id = db.new_id("term")
            conn.execute(sa.insert(t.term).values(id=term_id, name=name, definition=definition, synonyms=synonyms,
                                                  status="proposed", origin="manual", owner=actor))
        else:
            if not conn.execute(sa.update(t.term).where(t.term.c.id == term_id).values(
                    name=name, definition=definition, synonyms=synonyms, status="proposed", origin="manual",
                    version=t.term.c.version + 1, updated_at=sa.func.now())).rowcount:
                raise NotFound(f"term {term_id} not found")
        for ds in dataset_ids:
            conn.execute(pg_insert(t.term_binding).values(term_id=term_id, dataset_id=ds).on_conflict_do_nothing())
        db.audit(conn, actor, "upsert", "term", term_id, after={"name": name, "synonyms": synonyms})
    return {"id": term_id, "name": name, "status": "proposed"}


def create_relationship(from_field_id: str, to_field_id: str, actor: str) -> Dict[str, Any]:
    rel_id = db.new_id("rel")
    with db.tx() as conn:
        conn.execute(sa.insert(t.relationship).values(id=rel_id, from_field_id=from_field_id, to_field_id=to_field_id,
                                                      origin="manual", confidence=1.0, status="accepted"))
        db.audit(conn, actor, "create", "relationship", rel_id)
    return {"id": rel_id, "status": "accepted"}


upsert_measure = measures.upsert


# ---------------------------------------------------------------- search / ask
def search(query: str, kinds: List[str], k: int) -> List[Dict[str, Any]]:
    kinds = [x for x in kinds if x in KINDS] or list(KINDS)
    with db.tx() as conn:
        return [h.__dict__ for h in _search(conn, Embedder(), query, kinds, k)]


def ask(question: str, *, actor: str, role: str, mode: str, connection_id: Optional[str]) -> Dict[str, Any]:
    return _ask.ask(question, actor=actor, role=role, mode=mode, connection_id=connection_id)


def get_answer(answer_id: str) -> Dict[str, Any]:
    with db.tx() as conn:
        r = conn.execute(sa.select(t.answer).where(t.answer.c.id == answer_id)).first()
    if r is None:
        raise NotFound(f"answer {answer_id} not found")
    return _row(r)


def status() -> Dict[str, Any]:
    with db.tx() as conn:
        counts = {name: conn.execute(sa.select(sa.func.count()).select_from(tbl)).scalar_one()
                  for name, tbl in (("connections", t.connection), ("datasets", t.dataset), ("terms", t.term),
                                    ("relationships", t.relationship), ("measures", t.measure))}
        meta = conn.execute(sa.select(t.index_meta)).first()
    return {
        "enabled": True,
        "models": {r: {"base_url": endpoint(r).base_url, "model": endpoint(r).model} for r in ("reasoning", "fast", "embed")},
        "rerank_mode": rerank_mode(),
        "index": _row(meta) if meta else None,
        "counts": counts,
        "row_cap": config.row_cap(),
    }
