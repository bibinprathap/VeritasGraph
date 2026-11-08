"""Named SQL aggregate expressions, validated against the catalog on save."""

from __future__ import annotations

from typing import Any, Dict, Optional

import sqlalchemy as sa
import sqlglot
from sqlglot import exp

from veritasgraph.structured.connectors import DIALECTS
from veritasgraph.structured.errors import Conflict, Invalid, NotFound
from veritasgraph.structured.store import db
from veritasgraph.structured.store import schema as t


def _validate(expression: str, dialect: str, columns: set[str]) -> None:
    try:
        tree = sqlglot.parse_one(f"SELECT {expression} AS m FROM _t", read=dialect)
    except sqlglot.errors.ParseError as exc:
        raise Invalid(f"Expression does not parse: {exc}") from exc
    select = tree if isinstance(tree, exp.Select) else None
    if select is None or len(select.expressions) != 1:
        raise Invalid("A measure is exactly one expression.")
    if tree.find(exp.Subquery):
        raise Invalid("Subqueries are not allowed in a measure.")
    if not tree.find(exp.AggFunc):
        raise Invalid("A measure must aggregate (SUM, COUNT, AVG, MIN, MAX, ...).")
    unknown = {c.name for c in tree.find_all(exp.Column)} - columns
    if unknown:
        raise Invalid(f"Unknown column(s): {', '.join(sorted(unknown))}")


def upsert(*, name: str, expression: str, dataset_id: str, description: str = "", grain: Optional[str] = None,
           actor: str, measure_id: Optional[str] = None) -> Dict[str, Any]:
    with db.tx() as conn:
        ds = conn.execute(
            sa.select(t.dataset.c.id, t.connection.c.dialect)
            .join(t.connection, t.connection.c.id == t.dataset.c.connection_id)
            .where(t.dataset.c.id == dataset_id)
        ).first()
        if ds is None:
            raise NotFound(f"dataset {dataset_id} not found")
        cols = {r[0] for r in conn.execute(sa.select(t.field.c.name).where(t.field.c.dataset_id == dataset_id))}
        _validate(expression, DIALECTS[ds.dialect].sqlglot, cols)
        values = dict(name=name.strip(), expression=expression.strip(), dataset_id=dataset_id,
                      description=description.strip(), grain=grain)
        if measure_id is None:
            clash = conn.execute(sa.select(t.measure.c.id).where(sa.func.lower(t.measure.c.name) == name.strip().lower())).first()
            if clash:
                raise Conflict(f"A measure named '{name}' already exists.")
            measure_id = db.new_id("msr")
            conn.execute(sa.insert(t.measure).values(id=measure_id, owner=actor, status="proposed", **values))
            db.audit(conn, actor, "create", "measure", measure_id, after=values)
        else:
            before = conn.execute(sa.select(t.measure).where(t.measure.c.id == measure_id)).first()
            if before is None:
                raise NotFound(f"measure {measure_id} not found")
            # Editing a certified measure sends it back to review.
            conn.execute(sa.update(t.measure).where(t.measure.c.id == measure_id).values(
                status="proposed", version=t.measure.c.version + 1, updated_at=sa.func.now(), **values))
            db.audit(conn, actor, "update", "measure", measure_id,
                     before={"name": before.name, "expression": before.expression, "status": before.status},
                     after=values)
    return {"id": measure_id, **values, "status": "proposed"}
