"""Propose a business term and column roles for each changed dataset."""

from __future__ import annotations

import json
from typing import List, Literal

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert as pg_insert

from veritasgraph.llm import ChatClient, structured
from veritasgraph.structured.compile import prompt
from veritasgraph.structured.store import db
from veritasgraph.structured.store import schema as t

Role = Literal["id", "measure", "dimension", "time", "text", "other"]


class FieldRole(BaseModel):
    field: str
    role: Role


class DatasetDescription(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    definition: str = Field(max_length=500)
    synonyms: List[str] = Field(default_factory=list, max_length=8)
    fields: List[FieldRole]


def _payload(conn: sa.Connection, dataset_id: str) -> tuple[dict, set[str]]:
    ds = conn.execute(sa.select(t.dataset).where(t.dataset.c.id == dataset_id)).one()
    fields = conn.execute(
        sa.select(t.field).where(t.field.c.dataset_id == dataset_id).order_by(t.field.c.ordinal)
    ).all()
    return {
        "table": f"{ds.schema_name}.{ds.name}",
        "comment": ds.comment,
        "rows": ds.row_count,
        "columns": [
            {"name": f.name, "type": f.data_type, "pk": f.is_pk, "comment": f.comment, "examples": f.sample[:3]}
            for f in fields
        ],
    }, {f.name for f in fields}


def describe_dataset(client: ChatClient, dataset_id: str, actor: str = "compiler") -> str:
    with db.tx() as conn:
        payload, names = _payload(conn, dataset_id)
    result = structured(
        client,
        [{"role": "system", "content": prompt("describe_dataset")},
         {"role": "user", "content": json.dumps(payload, default=str)}],
        DatasetDescription,
    )
    with db.tx() as conn:
        existing = conn.execute(
            sa.select(t.term).where(sa.func.lower(t.term.c.name) == result.term.strip().lower())
        ).first()
        if existing is None:
            term_id = db.new_id("term")
            conn.execute(sa.insert(t.term).values(
                id=term_id, name=result.term.strip(), definition=result.definition.strip(),
                synonyms=[s.strip() for s in result.synonyms if s.strip()], status="proposed",
                origin="llm", owner=actor,
            ))
            db.audit(conn, actor, "propose", "term", term_id, after=result.model_dump())
        else:
            term_id = existing.id
            if existing.status == "proposed" and existing.origin == "llm":
                conn.execute(sa.update(t.term).where(t.term.c.id == term_id).values(
                    definition=result.definition.strip(), synonyms=result.synonyms, updated_at=sa.func.now(),
                ))
        conn.execute(pg_insert(t.term_binding).values(term_id=term_id, dataset_id=dataset_id).on_conflict_do_nothing())
        for fr in result.fields:
            if fr.field not in names:
                continue  # ignore invented columns
            conn.execute(
                sa.update(t.field)
                .where(t.field.c.dataset_id == dataset_id, t.field.c.name == fr.field,
                       sa.or_(t.field.c.role_origin.is_(None), t.field.c.role_origin == "llm"))
                .values(role=fr.role, role_origin="llm")
            )
    return term_id
