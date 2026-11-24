"""Infer joins between datasets of one connection.

1. Candidates: a column named like another table's single-column key
   (``customer_id`` -> ``customers.customer_id`` / ``customer.id``) with a
   compatible type family.
2. Evidence: share of sampled distinct child values found in the parent key.
3. Confidence from the evidence; stored as ``proposed`` for an editor to accept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from veritasgraph.structured.connectors import Source
from veritasgraph.structured.store import db
from veritasgraph.structured.store import schema as t

SAMPLE_VALUES = 200
MIN_CONTAINMENT = 0.9
_ID_COL = re.compile(r"^(?P<stem>[a-z0-9_]+?)_?(id|key|code|no)$", re.I)


def _family(data_type: str) -> str:
    d = data_type.upper()
    if any(x in d for x in ("INT", "SERIAL", "NUMBER", "NUMERIC", "DECIMAL")):
        return "number"
    if any(x in d for x in ("CHAR", "TEXT", "STRING", "VARCHAR")):
        return "text"
    if "UUID" in d:
        return "uuid"
    if "DATE" in d or "TIME" in d:
        return "time"
    return d


def _singular(word: str) -> str:
    w = word.lower()
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith(("ses", "xes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


@dataclass
class FieldRef:
    field_id: str
    dataset_id: str
    schema: str
    table: str
    column: str
    data_type: str
    is_pk: bool


@dataclass
class Candidate:
    child: FieldRef
    parent: FieldRef
    reason: str


def _load(conn: sa.Connection, connection_id: str) -> List[FieldRef]:
    rows = conn.execute(
        sa.select(t.field.c.id, t.dataset.c.id.label("ds"), t.dataset.c.schema_name, t.dataset.c.name.label("tbl"),
                  t.field.c.name, t.field.c.data_type, t.field.c.is_pk)
        .join(t.dataset, t.field.c.dataset_id == t.dataset.c.id)
        .where(t.dataset.c.connection_id == connection_id)
    )
    return [FieldRef(r.id, r.ds, r.schema_name, r.tbl, r.name, r.data_type, r.is_pk) for r in rows]


def candidates(fields: List[FieldRef]) -> List[Candidate]:
    pks_by_ds: Dict[str, List[FieldRef]] = {}
    for f in fields:
        if f.is_pk:
            pks_by_ds.setdefault(f.dataset_id, []).append(f)
    single_pk = {ds: pks[0] for ds, pks in pks_by_ds.items() if len(pks) == 1}
    by_stem: Dict[str, FieldRef] = {}
    by_name: Dict[str, List[FieldRef]] = {}
    for pk in single_pk.values():
        by_stem[_singular(pk.table)] = pk
        by_name.setdefault(pk.column.lower(), []).append(pk)

    out: List[Candidate] = []
    seen = set()
    for f in fields:
        if single_pk.get(f.dataset_id) is f:
            continue
        options: List[FieldRef] = list(by_name.get(f.column.lower(), []))
        m = _ID_COL.match(f.column)
        if m and (stem_pk := by_stem.get(_singular(m.group("stem").rstrip("_")))) is not None:
            options.append(stem_pk)
        for parent in options:
            key = (f.field_id, parent.field_id)
            if parent.dataset_id == f.dataset_id or key in seen:
                continue
            if _family(parent.data_type) != _family(f.data_type):
                continue
            seen.add(key)
            out.append(Candidate(f, parent, "name"))
    return out


def evidence(src: Source, c: Candidate) -> Dict[str, float]:
    values = src.distinct_values(c.child.schema, c.child.table, c.child.column, SAMPLE_VALUES)
    if not values:
        return {"sampled": 0, "containment": 0.0}
    found = src.count_contained(c.parent.schema, c.parent.table, c.parent.column, values)
    return {"sampled": len(values), "containment": round(found / len(values), 4)}


def confidence(ev: Dict[str, float]) -> float:
    if not ev["sampled"]:
        return 0.0
    small_sample_penalty = 0.1 if ev["sampled"] < 5 else 0.0
    return round(max(0.0, 0.4 + 0.6 * ev["containment"] - small_sample_penalty), 3)


def infer(connection_id: str, src: Source, actor: str = "compiler") -> Dict[str, int]:
    with db.tx() as conn:
        fields = _load(conn, connection_id)
        known = {(r.from_field_id, r.to_field_id) for r in conn.execute(
            sa.select(t.relationship.c.from_field_id, t.relationship.c.to_field_id))}
    stats = {"candidates": 0, "proposed": 0}
    for c in candidates(fields):
        if (c.child.field_id, c.parent.field_id) in known:
            continue
        stats["candidates"] += 1
        ev = evidence(src, c)
        if ev["containment"] < MIN_CONTAINMENT:
            continue
        with db.tx() as conn:
            rel_id = db.new_id("rel")
            conn.execute(pg_insert(t.relationship).values(
                id=rel_id, from_field_id=c.child.field_id, to_field_id=c.parent.field_id, origin="inferred",
                confidence=confidence(ev), evidence={**ev, "reason": c.reason}, status="proposed",
            ).on_conflict_do_nothing())
            db.audit(conn, actor, "propose", "relationship", rel_id, after=ev)
        stats["proposed"] += 1
    _mark_bridges(connection_id)
    return stats


def _mark_bridges(connection_id: str) -> None:
    """Tables that mostly hold two or more keys to other tables are many-to-many links."""
    with db.tx() as conn:
        out_counts = dict(conn.execute(
            sa.select(t.field.c.dataset_id, sa.func.count(sa.distinct(t.relationship.c.to_field_id)))
            .join(t.relationship, t.relationship.c.from_field_id == t.field.c.id)
            .where(t.relationship.c.status.in_(("proposed", "accepted", "certified")))
            .group_by(t.field.c.dataset_id)
        ).all())
        for ds_id, n_out in out_counts.items():
            other = conn.execute(
                sa.select(sa.func.count()).select_from(t.field)
                .where(t.field.c.dataset_id == ds_id, t.field.c.is_pk.is_(False),
                       sa.or_(t.field.c.role.is_(None), t.field.c.role.not_in(("id",))))
            ).scalar_one()
            conn.execute(sa.update(t.dataset).where(t.dataset.c.id == ds_id)
                         .values(is_bridge=bool(n_out >= 2 and other - n_out <= 1)))
