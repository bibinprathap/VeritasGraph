"""Jobs live in vg_structured.job; Studio runs one in-process worker loop."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Dict, Optional

import sqlalchemy as sa

from veritasgraph.llm import ChatClient, Embedder, endpoint
from veritasgraph.structured import catalog
from veritasgraph.structured.compile import relationships, terms
from veritasgraph.structured.search import refresh, reset_index
from veritasgraph.structured.store import db
from veritasgraph.structured.store import schema as t

log = logging.getLogger("veritasgraph.structured.worker")
KINDS = ("sync", "compile", "reindex")


def enqueue(kind: str, actor: str, connection_id: Optional[str] = None) -> str:
    if kind not in KINDS:
        raise ValueError(kind)
    job_id = db.new_id("job")
    with db.tx() as conn:
        conn.execute(sa.insert(t.job).values(id=job_id, kind=kind, connection_id=connection_id, requested_by=actor))
    return job_id


def recover() -> None:
    """Jobs left 'running' by a crash are marked failed so they can be re-requested."""
    with db.tx() as conn:
        conn.execute(sa.update(t.job).where(t.job.c.status == "running")
                     .values(status="failed", error="interrupted", finished_at=sa.func.now()))


def _claim() -> Optional[Any]:
    with db.tx() as conn:
        row = conn.execute(sa.select(t.job).where(t.job.c.status == "queued").order_by(t.job.c.created_at)
                           .limit(1).with_for_update(skip_locked=True)).first()
        if row is not None:
            conn.execute(sa.update(t.job).where(t.job.c.id == row.id).values(status="running", started_at=sa.func.now()))
        return row


def _compile(connection_id: str, dataset_ids, actor: str) -> Dict[str, Any]:
    client = ChatClient(endpoint("reasoning"))
    described, failed = 0, []
    for ds_id in dataset_ids:
        try:
            terms.describe_dataset(client, ds_id, actor)
            described += 1
        except Exception as exc:  # noqa: BLE001 - one bad table must not stop the run
            log.warning("describe_dataset failed for %s: %s", ds_id, exc)
            failed.append(ds_id)
    _, src = catalog.open_source(connection_id)
    rel = relationships.infer(connection_id, src, actor)
    with db.tx() as conn:
        embedded = refresh(conn, Embedder())
    return {"described": described, "failed": failed, "relationships": rel, "embedded": embedded}


def _run(job: Any) -> Dict[str, Any]:
    if job.kind == "sync":
        stats = catalog.sync(job.connection_id)
        stats["compile"] = _compile(job.connection_id, stats["changed_dataset_ids"], job.requested_by)
        return stats
    if job.kind == "compile":
        with db.tx() as conn:
            ids = [r[0] for r in conn.execute(sa.select(t.dataset.c.id).where(t.dataset.c.connection_id == job.connection_id))]
        return _compile(job.connection_id, ids, job.requested_by)
    with db.tx() as conn:  # reindex
        reset_index(conn)
        return {"embedded": refresh(conn, Embedder())}


async def run_forever(stop: asyncio.Event, poll_s: float = 2.0) -> None:
    await asyncio.to_thread(recover)
    while not stop.is_set():
        job = await asyncio.to_thread(_claim)
        if job is None:
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(stop.wait(), poll_s)
            continue
        try:
            stats = await asyncio.to_thread(_run, job)
            values = {"status": "done", "stats": stats}
        except Exception as exc:  # noqa: BLE001 - recorded on the job row
            log.exception("job %s failed", job.id)
            values = {"status": "failed", "error": str(exc)[:500]}
        await asyncio.to_thread(_finish, job.id, values)


def _finish(job_id: str, values: Dict[str, Any]) -> None:
    with db.tx() as conn:
        conn.execute(sa.update(t.job).where(t.job.c.id == job_id).values(finished_at=sa.func.now(), **values))
