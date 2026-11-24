"""Turn search hits into the tables, joins, terms and measures the SQL may use."""

from __future__ import annotations

import itertools
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import networkx as nx
import sqlalchemy as sa

from veritasgraph.structured.errors import Invalid
from veritasgraph.structured.search import Hit
from veritasgraph.structured.store import schema as t

MAX_DATASETS = 8
JOIN_STATUSES = ("accepted", "certified")


@dataclass
class Context:
    connection_id: str
    dialect: str
    dataset_ids: List[str]
    allowed_tables: Set[str]
    text: str
    joins: List[Dict[str, str]] = field(default_factory=list)
    terms: List[Dict[str, str]] = field(default_factory=list)
    measures: List[Dict[str, str]] = field(default_factory=list)


def _hit_datasets(conn: sa.Connection, hits: List[Hit]) -> Dict[str, float]:
    score: Dict[str, float] = defaultdict(float)
    by_kind = defaultdict(list)
    for h in hits:
        by_kind[h.kind].append(h)
    for h in by_kind["dataset"]:
        score[h.id] += h.score
    if by_kind["field"]:
        for fid, ds in conn.execute(sa.select(t.field.c.id, t.field.c.dataset_id)
                                    .where(t.field.c.id.in_([h.id for h in by_kind["field"]]))):
            score[ds] += next(h.score for h in by_kind["field"] if h.id == fid)
    if by_kind["measure"]:
        for mid, ds in conn.execute(sa.select(t.measure.c.id, t.measure.c.dataset_id)
                                    .where(t.measure.c.id.in_([h.id for h in by_kind["measure"]]))):
            score[ds] += next(h.score for h in by_kind["measure"] if h.id == mid)
    if by_kind["term"]:
        for tid, ds in conn.execute(sa.select(t.term_binding.c.term_id, t.term_binding.c.dataset_id)
                                    .where(t.term_binding.c.term_id.in_([h.id for h in by_kind["term"]]))):
            score[ds] += next(h.score for h in by_kind["term"] if h.id == tid)
    return score


def build(conn: sa.Connection, hits: List[Hit], connection_id: Optional[str]) -> Context:
    ds_score = _hit_datasets(conn, hits)
    if not ds_score:
        raise Invalid("Nothing in the catalog matches this question.")
    ds_rows = {r.id: r for r in conn.execute(sa.select(t.dataset).where(t.dataset.c.id.in_(list(ds_score))))}
    if connection_id is None:
        per_conn: Dict[str, float] = defaultdict(float)
        for ds_id, s in ds_score.items():
            per_conn[ds_rows[ds_id].connection_id] += s
        ranked = sorted(per_conn.items(), key=lambda kv: kv[1], reverse=True)
        if len(ranked) > 1 and ranked[1][1] >= 0.8 * ranked[0][1]:
            raise Invalid("The question matches several connections equally; pass connection_id.")
        connection_id = ranked[0][0]
    chosen = [d for d, _ in sorted(ds_score.items(), key=lambda kv: kv[1], reverse=True)
              if ds_rows[d].connection_id == connection_id][:MAX_DATASETS]
    if not chosen:
        raise Invalid("Nothing in this connection matches the question.")

    # Join graph over accepted relationships of this connection.
    rels = conn.execute(
        sa.select(t.relationship.c.id, t.relationship.c.from_field_id, t.relationship.c.to_field_id)
        .where(t.relationship.c.status.in_(JOIN_STATUSES))
    ).all()
    fields = {r.id: r for r in conn.execute(
        sa.select(t.field.c.id, t.field.c.name, t.field.c.dataset_id, t.dataset.c.connection_id)
        .join(t.dataset, t.dataset.c.id == t.field.c.dataset_id)
        .where(t.dataset.c.connection_id == connection_id))}
    graph = nx.Graph()
    for r in rels:
        a, b = fields.get(r.from_field_id), fields.get(r.to_field_id)
        if a and b:
            graph.add_edge(a.dataset_id, b.dataset_id, rel=(a, b))
    needed = set(chosen)
    for x, y in itertools.combinations(chosen, 2):
        if graph.has_node(x) and graph.has_node(y) and nx.has_path(graph, x, y):
            needed.update(nx.shortest_path(graph, x, y))
    extra = needed - set(ds_rows)
    if extra:
        ds_rows.update({r.id: r for r in conn.execute(sa.select(t.dataset).where(t.dataset.c.id.in_(list(extra))))})

    dialect = conn.execute(sa.select(t.connection.c.dialect).where(t.connection.c.id == connection_id)).scalar_one()
    from veritasgraph.structured.connectors import DIALECTS

    allowed: Set[str] = set()
    bare = defaultdict(int)
    lines: List[str] = ["TABLES"]
    for ds_id in needed:
        d = ds_rows[ds_id]
        allowed.add(f"{d.schema_name}.{d.name}".lower())
        bare[d.name.lower()] += 1
        lines.append(f"- {d.schema_name}.{d.name} (~{d.row_count if d.row_count is not None else '?'} rows)"
                     + (f" -- {d.comment}" if d.comment else ""))
        for f in conn.execute(sa.select(t.field).where(t.field.c.dataset_id == ds_id).order_by(t.field.c.ordinal)):
            examples = "" if f.pii_class else f" e.g. {json.dumps(f.sample[:3], default=str)}" if f.sample else ""
            lines.append(f"    {f.name} {f.data_type}" + (f" [{f.role}]" if f.role else "")
                         + (" PK" if f.is_pk else "") + (f" -- {f.comment}" if f.comment else "") + examples)
    allowed.update(name for name, n in bare.items() if n == 1)

    joins = []
    lines.append("RELATIONSHIPS")
    for u, v, data in graph.edges(data=True):
        if u in needed and v in needed:
            a, b = data["rel"]
            da, db_ = ds_rows[a.dataset_id], ds_rows[b.dataset_id]
            join = {"left": f"{da.schema_name}.{da.name}.{a.name}", "right": f"{db_.schema_name}.{db_.name}.{b.name}"}
            joins.append(join)
            lines.append(f"- {join['left']} = {join['right']}")

    terms = [dict(r._mapping) for r in conn.execute(
        sa.select(t.term.c.id, t.term.c.name, t.term.c.definition, t.term.c.status)
        .join(t.term_binding, t.term_binding.c.term_id == t.term.c.id)
        .where(t.term_binding.c.dataset_id.in_(list(needed)), t.term.c.status != "rejected").distinct())]
    measures = [dict(r._mapping) for r in conn.execute(
        sa.select(t.measure.c.id, t.measure.c.name, t.measure.c.expression, t.measure.c.status, t.measure.c.dataset_id)
        .where(t.measure.c.dataset_id.in_(list(needed)), t.measure.c.status != "rejected"))]
    if terms:
        lines.append("TERMS")
        lines += [f"- {x['name']} ({x['status']}): {x['definition']}" for x in terms]
    if measures:
        lines.append("MEASURES")
        for m in measures:
            d = ds_rows[m["dataset_id"]]
            lines.append(f"- {m['name']} ({m['status']}) on {d.schema_name}.{d.name}: {m['expression']}")

    return Context(connection_id, DIALECTS[dialect].sqlglot, list(needed), allowed, "\n".join(lines),
                   joins, terms, measures)
