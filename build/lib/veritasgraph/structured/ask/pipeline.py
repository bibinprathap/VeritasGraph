"""route -> search -> coverage -> generate -> validate -> explain/repair -> run -> answer -> receipt."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import sqlalchemy as sa

from veritasgraph import pii
from veritasgraph.llm import ChatClient, Embedder, LLMError, endpoint, structured
from veritasgraph.structured import config
from veritasgraph.structured.ask import context as ctx_mod
from veritasgraph.structured.ask import coverage
from veritasgraph.structured.ask.models import Route, SqlDraft
from veritasgraph.structured.ask.validate import validate
from veritasgraph.structured.catalog import open_source
from veritasgraph.structured.compile import prompt
from veritasgraph.structured.errors import Invalid, SqlRejected
from veritasgraph.structured.search import search
from veritasgraph.structured.store import db
from veritasgraph.structured.store import schema as t

REPAIRS = 2
ANSWER_ROWS = 50


def _short(exc: BaseException) -> str:
    text = str(getattr(exc, "orig", None) or exc).strip().splitlines()[0]
    return text[:400]


def _mask_rows(columns: List[str], rows: List[List[Any]], pii_columns: set[str], role: str) -> List[List[Any]]:
    if pii.can_see_pii(role):
        return rows
    hide = [c.lower() in pii_columns for c in columns]
    return [["[REDACTED]" if h else (pii.redact(v) if isinstance(v, str) else v) for v, h in zip(r, hide)]
            for r in rows]


def _finish(question: str, actor: str, status: str, receipt: Dict[str, Any], sql: Optional[str] = None) -> Dict[str, Any]:
    answer_id = db.new_id("ans")
    with db.tx() as conn:
        conn.execute(sa.insert(t.answer).values(id=answer_id, question=question, actor=actor, status=status,
                                                sql=sql, receipt=receipt))
    return {"answer_id": answer_id, "status": status, "sql": sql, **receipt}


def ask(question: str, *, actor: str, role: str, mode: str = "exploratory",
        connection_id: Optional[str] = None) -> Dict[str, Any]:
    started = time.monotonic()
    fast, reasoning, emb = ChatClient(endpoint("fast")), ChatClient(endpoint("reasoning")), Embedder()
    models = {"fast": fast.ep.model, "reasoning": reasoning.ep.model, "embed": emb.ep.model}
    receipt: Dict[str, Any] = {"mode": mode, "models": models}

    route = structured(fast, [{"role": "system", "content": prompt("route")},
                              {"role": "user", "content": question}], Route)
    receipt["route"] = route.model_dump()
    if route.target == "out_of_scope":
        return _finish(question, actor, "out_of_scope", {**receipt, "answer": None, "reason": route.reason})
    if route.target == "documents":
        return _finish(question, actor, "routed_documents", {**receipt, "answer": None})

    with db.tx() as conn:
        cov = coverage.check(conn, emb, fast, question, mode)
        receipt["coverage"] = cov.concepts
        if not cov.ok:
            return _finish(question, actor, "no_coverage", {**receipt, "answer": None, "reason": cov.reason})
        hits = search(conn, emb, question, k=12)
        try:
            ctx = ctx_mod.build(conn, hits, connection_id)
        except Invalid as exc:
            return _finish(question, actor, "no_coverage", {**receipt, "answer": None, "reason": str(exc)})
        pii_columns = {r[0].lower() for r in conn.execute(
            sa.select(t.field.c.name).where(t.field.c.dataset_id.in_(ctx.dataset_ids), t.field.c.pii_class.is_not(None)))}

    receipt.update({"connection_id": ctx.connection_id, "datasets": ctx.dataset_ids, "joins": ctx.joins,
                    "terms": [{"id": x["id"], "name": x["name"], "status": x["status"]} for x in ctx.terms],
                    "measures": [{"id": x["id"], "name": x["name"], "status": x["status"]} for x in ctx.measures]})
    _, src = open_source(ctx.connection_id)

    system = prompt("generate_sql").replace("{dialect}", ctx.dialect)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": f"CONTEXT\n{ctx.text}\n\nQUESTION\n{question}"}]
    sql: Optional[str] = None
    draft: Optional[SqlDraft] = None
    errors: List[str] = []
    for _ in range(1 + REPAIRS):
        try:
            draft = structured(reasoning, messages, SqlDraft)
            sql = validate(draft.sql, ctx.dialect, ctx.allowed_tables, config.row_cap())
            src.explain(sql)
            break
        except (SqlRejected, sa.exc.DBAPIError, sa.exc.StatementError, LLMError) as exc:
            errors.append(_short(exc))
            sql = None
            if draft is not None:
                messages += [{"role": "assistant", "content": draft.model_dump_json()},
                             {"role": "user", "content": f"That query failed: {errors[-1]}. Fix it and reply with JSON only."}]
    receipt["attempt_errors"] = errors
    if sql is None:
        return _finish(question, actor, "rejected", {**receipt, "answer": None, "reason": errors[-1] if errors else None})

    try:
        columns, rows, truncated = src.run(sql, config.row_cap())
    except Exception as exc:  # noqa: BLE001 - surface a safe one-line error
        return _finish(question, actor, "error", {**receipt, "answer": None, "reason": _short(exc)}, sql)
    shown = _mask_rows(columns, rows, pii_columns, role)

    prose = fast.complete([
        {"role": "system", "content": prompt("answer")},
        {"role": "user", "content": json.dumps({"question": question, "columns": columns,
                                                "rows": shown[:ANSWER_ROWS], "truncated": truncated}, default=str)},
    ])
    receipt.update({"answer": prose.strip(), "columns": columns, "rows": shown, "row_count": len(rows),
                    "truncated": truncated, "assumptions": draft.assumptions if draft else [],
                    "elapsed_ms": int((time.monotonic() - started) * 1000)})
    return _finish(question, actor, "answered", receipt, sql)
