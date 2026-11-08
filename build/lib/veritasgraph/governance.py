"""Governance: tamper-evident audit trail, graph snapshots, answer receipts.

* **Audit.** Every governed write (ingest, import, clear, restore, ontology
  changes, certification, suggestion decisions) appends an ``audit_event`` row.
  Each row's hash covers the previous row's hash plus its own content, so
  :func:`verify_audit` detects any edit, deletion or reordering.
* **Snapshots.** A compressed copy of the graph and term links. Taken
  automatically before destructive operations (clear, overwrite import,
  restore) so they can be undone.
* **Answer receipts.** What an answer was based on — seeds, subgraph, cited
  sources, graph version — so a later audit can reproduce or challenge it.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
import zlib
from typing import Any, Dict, List, Optional

from veritasgraph.store.sqlite import SqliteGraphStore

_GENESIS = "0" * 64


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _event_hash(prev_hash: str, ts: float, actor: str, action: str, target: str, detail: str) -> str:
    payload = _canonical([prev_hash, repr(ts), actor, action, target, detail])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #
def record_audit(
    store: SqliteGraphStore,
    actor: str,
    action: str,
    target: str = "",
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    detail_json = _canonical(detail or {})
    with store.transaction() as conn:
        row = conn.execute("SELECT hash FROM audit_event ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else _GENESIS
        ts = time.time()
        digest = _event_hash(prev, ts, actor or "", action, target or "", detail_json)
        cur = conn.execute(
            "INSERT INTO audit_event(ts, actor, action, target, detail, prev_hash, hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, actor or "", action, target or "", detail_json, prev, digest),
        )
        seq = cur.lastrowid
    return {"seq": seq, "hash": digest}


def list_audit(
    store: SqliteGraphStore, limit: int = 100, action: Optional[str] = None
) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    if action:
        rows = store.conn.execute(
            "SELECT * FROM audit_event WHERE action = ? ORDER BY seq DESC LIMIT ?", (action, limit)
        )
    else:
        rows = store.conn.execute("SELECT * FROM audit_event ORDER BY seq DESC LIMIT ?", (limit,))
    return [{**dict(r), "detail": json.loads(r["detail"])} for r in rows]


def verify_audit(store: SqliteGraphStore) -> Dict[str, Any]:
    prev = _GENESIS
    count = 0
    for row in store.conn.execute("SELECT * FROM audit_event ORDER BY seq"):
        expected = _event_hash(prev, row["ts"], row["actor"], row["action"], row["target"], row["detail"])
        if row["prev_hash"] != prev or row["hash"] != expected:
            return {"ok": False, "events": count, "broken_at": row["seq"]}
        prev = row["hash"]
        count += 1
    return {"ok": True, "events": count, "head": prev}


# --------------------------------------------------------------------------- #
# Snapshots
# --------------------------------------------------------------------------- #
def _keep() -> int:
    try:
        return max(1, int(os.getenv("VERITASGRAPH_SNAPSHOT_KEEP", "20")))
    except ValueError:
        return 20


def create_snapshot(store: SqliteGraphStore, label: str = "", actor: str = "") -> Dict[str, Any]:
    with store.transaction() as conn:
        version, _epoch, sources, entities, rels = store.load_all()
        links = [tuple(r) for r in conn.execute("SELECT term_id, entity_id FROM term_entity")]
        body = zlib.compress(
            _canonical(
                {"sources": sources, "entities": entities, "relationships": rels, "term_entity": links}
            ).encode("utf-8")
        )
        snap_id = f"snap_{uuid.uuid4().hex[:10]}"
        counts = {"sources": len(sources), "entities": len(entities), "relationships": len(rels)}
        conn.execute(
            "INSERT INTO snapshot(id, label, created_at, created_by, graph_version, counts, body) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snap_id, (label or "")[:200], time.time(), actor or "", version, _canonical(counts), body),
        )
        # Retention: drop the oldest beyond the limit.
        conn.execute(
            "DELETE FROM snapshot WHERE id NOT IN "
            "(SELECT id FROM snapshot ORDER BY created_at DESC LIMIT ?)",
            (_keep(),),
        )
    return {"id": snap_id, "label": label, "graph_version": version, "counts": counts}


def list_snapshots(store: SqliteGraphStore) -> List[Dict[str, Any]]:
    rows = store.conn.execute(
        "SELECT id, label, created_at, created_by, graph_version, counts FROM snapshot "
        "ORDER BY created_at DESC"
    )
    return [{**dict(r), "counts": json.loads(r["counts"])} for r in rows]


def load_snapshot(store: SqliteGraphStore, snap_id: str) -> Dict[str, Any]:
    row = store.conn.execute("SELECT body FROM snapshot WHERE id = ?", (snap_id,)).fetchone()
    if row is None:
        raise KeyError(snap_id)
    return json.loads(zlib.decompress(row["body"]).decode("utf-8"))


def restore_term_links(store: SqliteGraphStore, links: List[List[str]]) -> None:
    with store.transaction() as conn:
        conn.execute("DELETE FROM term_entity")
        for term_id, entity_id in links:
            if conn.execute("SELECT 1 FROM term WHERE id = ?", (term_id,)).fetchone():
                conn.execute(
                    "INSERT OR IGNORE INTO term_entity(term_id, entity_id) VALUES (?, ?)",
                    (term_id, entity_id),
                )


# --------------------------------------------------------------------------- #
# Answer receipts and feedback
# --------------------------------------------------------------------------- #
def record_answer(
    store: SqliteGraphStore,
    *,
    question: str,
    answer: str,
    mode: str,
    model: str,
    grounded: bool,
    abstained: bool,
    evidence: Dict[str, Any],
    actor: str = "",
) -> str:
    answer_id = f"ans_{uuid.uuid4().hex[:12]}"
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO answer_log(id, ts, actor, mode, model, question, answer, grounded, "
            "abstained, graph_version, evidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                answer_id,
                time.time(),
                actor,
                mode,
                model,
                question,
                answer,
                int(grounded),
                int(abstained),
                store.graph_version(),
                _canonical(evidence),
            ),
        )
    return answer_id


def get_answer(store: SqliteGraphStore, answer_id: str) -> Optional[Dict[str, Any]]:
    row = store.conn.execute("SELECT * FROM answer_log WHERE id = ?", (answer_id,)).fetchone()
    if row is None:
        return None
    out = {**dict(row), "evidence": json.loads(row["evidence"])}
    out["grounded"] = bool(out["grounded"])
    out["abstained"] = bool(out["abstained"])
    out["graph_changed_since"] = store.graph_version() != row["graph_version"]
    out["feedback"] = [
        dict(r)
        for r in store.conn.execute(
            "SELECT id, ts, actor, rating, comment FROM feedback WHERE answer_id = ? ORDER BY ts",
            (answer_id,),
        )
    ]
    return out


def add_feedback(
    store: SqliteGraphStore, answer_id: str, rating: int, comment: str = "", actor: str = ""
) -> Dict[str, Any]:
    if rating not in (-1, 0, 1):
        raise ValueError("rating must be -1, 0 or 1")
    fb_id = f"fb_{uuid.uuid4().hex[:10]}"
    with store.transaction() as conn:
        if not conn.execute("SELECT 1 FROM answer_log WHERE id = ?", (answer_id,)).fetchone():
            raise KeyError(answer_id)
        conn.execute(
            "INSERT INTO feedback(id, answer_id, ts, actor, rating, comment) VALUES (?, ?, ?, ?, ?, ?)",
            (fb_id, answer_id, time.time(), actor, rating, (comment or "")[:2000]),
        )
    return {"id": fb_id, "answer_id": answer_id, "rating": rating}
