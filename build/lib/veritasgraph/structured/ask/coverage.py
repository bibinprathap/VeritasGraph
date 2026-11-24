"""Refuse to generate SQL when a concept the question needs has no catalog mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import sqlalchemy as sa

from veritasgraph.llm import ChatClient, Embedder, structured
from veritasgraph.structured import config
from veritasgraph.structured.ask.models import Concepts
from veritasgraph.structured.compile import prompt
from veritasgraph.structured.search import search
from veritasgraph.structured.store import schema as t


@dataclass
class Coverage:
    ok: bool
    concepts: List[Dict[str, object]] = field(default_factory=list)
    reason: str | None = None


def check(conn: sa.Connection, emb: Embedder, fast: ChatClient, question: str, mode: str) -> Coverage:
    if not config.ask_coverage_enabled():
        return Coverage(True)
    found = structured(fast, [{"role": "system", "content": prompt("concepts")},
                              {"role": "user", "content": question}], Concepts)
    threshold = config.ask_min_similarity()
    rows: List[Dict[str, object]] = []
    uncovered: List[str] = []
    for concept in found.concepts:
        hits = search(conn, emb, concept, k=3)
        best = max(hits, key=lambda h: max(h.similarity, h.name_match), default=None)
        strength = max(best.similarity, best.name_match) if best else 0.0
        covered = best is not None and strength >= threshold
        if covered and mode == "governed":
            covered = _certified(conn, best.kind, best.id)
        rows.append({"concept": concept, "covered": covered, "kind": best.kind if best else None,
                     "id": best.id if best else None, "name": best.name if best else None,
                     "strength": round(strength, 3)})
        if not covered:
            uncovered.append(concept)
    if uncovered:
        need = "certified " if mode == "governed" else ""
        return Coverage(False, rows, f"No {need}catalog mapping for: {', '.join(uncovered)}.")
    return Coverage(True, rows)


def _certified(conn: sa.Connection, kind: str, obj_id: str) -> bool:
    if kind == "term":
        return conn.execute(sa.select(t.term.c.status).where(t.term.c.id == obj_id)).scalar() == "certified"
    if kind == "measure":
        return conn.execute(sa.select(t.measure.c.status).where(t.measure.c.id == obj_id)).scalar() == "certified"
    if kind in ("dataset", "field"):
        ds_col = t.dataset.c.id if kind == "dataset" else t.field.c.dataset_id
        table = t.dataset if kind == "dataset" else t.field
        ds_id = conn.execute(sa.select(ds_col).select_from(table).where(table.c.id == obj_id)).scalar()
        return bool(conn.execute(
            sa.select(sa.func.count()).select_from(t.term_binding.join(t.term, t.term.c.id == t.term_binding.c.term_id))
            .where(t.term_binding.c.dataset_id == ds_id, t.term.c.status == "certified")).scalar())
    return False
