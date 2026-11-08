"""Compile: periodic, deterministic clean-up of the graph against the ontology.

Each run executes these stages in order and records them in ``compile_run``:

1. ``normalize_types``      — map entity types onto certified types via synonyms;
2. ``normalize_predicates`` — map relationship predicates (or their descriptions)
   onto certified predicates;
3. ``merge_candidates``     — group entities whose names differ only by case,
   punctuation, a corporate suffix or a plural; *suggest* merges, never merge;
4. ``suggest_terms``        — suggest glossary terms for well-connected entities
   that no term covers;
5. ``check_predicate_rules`` — flag relationships that violate a certified
   predicate's domain/range;
6. ``detect_orphans``       — flag entities with no relationships.

Stages 1–2 change the graph only where the mapping is unambiguous (certified
vocabulary). Everything else becomes a ``suggestion`` a human accepts or rejects;
suggestion fingerprints make a rejected one stay rejected across runs.

A ``job_lock`` row ensures only one process (Studio, MCP, CLI) compiles at a time.
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from veritasgraph import governance
from veritasgraph.ontology import key
from veritasgraph.store.sqlite import SqliteGraphStore

LOCK_NAME = "compile"
_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "ltd", "limited", "llc", "co",
             "company", "plc", "gmbh", "the"}
_MAX_PER_STAGE = 200


# --------------------------------------------------------------------------- #
# Lock
# --------------------------------------------------------------------------- #
def acquire_lock(store: SqliteGraphStore, name: str, holder: str, ttl: float = 600.0) -> bool:
    now = time.time()
    with store.transaction() as conn:
        conn.execute("DELETE FROM job_lock WHERE name = ? AND expires_at < ?", (name, now))
        conn.execute(
            "INSERT OR IGNORE INTO job_lock(name, holder, expires_at) VALUES (?, ?, ?)",
            (name, holder, now + ttl),
        )
        row = conn.execute("SELECT holder FROM job_lock WHERE name = ?", (name,)).fetchone()
    return row is not None and row["holder"] == holder


def release_lock(store: SqliteGraphStore, name: str, holder: str) -> None:
    with store.transaction() as conn:
        conn.execute("DELETE FROM job_lock WHERE name = ? AND holder = ?", (name, holder))


# --------------------------------------------------------------------------- #
# Suggestions
# --------------------------------------------------------------------------- #
def _suggest(store: SqliteGraphStore, run_id: str, kind: str, fingerprint: str, payload: Dict[str, Any]) -> bool:
    cur = store.conn.execute(
        "INSERT OR IGNORE INTO suggestion(id, kind, fingerprint, status, run_id, payload, created_at) "
        "VALUES (?, ?, ?, 'open', ?, ?, ?)",
        (f"sug_{uuid.uuid4().hex[:10]}", kind, fingerprint, run_id, json.dumps(payload), time.time()),
    )
    return cur.rowcount > 0


def list_suggestions(
    store: SqliteGraphStore, status: str = "open", kind: Optional[str] = None, limit: int = 200
) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    sql = "SELECT * FROM suggestion WHERE status = ?"
    params: List[Any] = [status]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    return [{**dict(r), "payload": json.loads(r["payload"])} for r in store.conn.execute(sql, params)]


def resolve_suggestion(engine: Any, suggestion_id: str, accept: bool, actor: str = "system") -> Dict[str, Any]:
    store: SqliteGraphStore = engine.store
    row = store.conn.execute("SELECT * FROM suggestion WHERE id = ?", (suggestion_id,)).fetchone()
    if row is None:
        raise KeyError(suggestion_id)
    if row["status"] != "open":
        raise ValueError(f"suggestion is already {row['status']}")
    payload = json.loads(row["payload"])
    outcome: Dict[str, Any] = {}
    if accept:
        if row["kind"] == "merge":
            merged = []
            for drop in payload["entity_ids"]:
                if drop != payload["keep_id"] and drop in engine.entities:
                    merged.append(engine.merge_entities(payload["keep_id"], drop, actor=actor))
            outcome["merged"] = merged
        elif row["kind"] == "term":
            term = engine.ontology.upsert_term(
                payload["name"],
                definition=payload.get("definition", ""),
                entity_ids=[payload["entity_id"]] if payload["entity_id"] in engine.entities else [],
                owner_id=actor,
            )
            outcome["term_id"] = term["id"]
    status = "accepted" if accept else "rejected"
    with store.transaction() as conn:
        conn.execute(
            "UPDATE suggestion SET status = ?, resolved_at = ?, resolved_by = ? WHERE id = ?",
            (status, time.time(), actor, suggestion_id),
        )
        governance.record_audit(
            store, actor, f"suggestion.{status}", suggestion_id, {"kind": row["kind"], **outcome}
        )
    return {"id": suggestion_id, "status": status, **outcome}


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #
def _canonical_name(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    words = [w for w in words if w not in _SUFFIXES]
    if words and len(words[-1]) > 3 and words[-1].endswith("s") and not words[-1].endswith("ss"):
        words[-1] = words[-1][:-1]
    return " ".join(words)


def _degree(engine: Any) -> Dict[str, int]:
    degree = {eid: 0 for eid in engine.entities}
    for rel in engine.relationships.values():
        degree[rel["source"]] = degree.get(rel["source"], 0) + 1
        degree[rel["target"]] = degree.get(rel["target"], 0) + 1
    return degree


def _normalize_types(engine: Any, run_id: str, actor: str) -> Dict[str, Any]:
    vocab = engine.ontology.vocabulary()
    if not vocab.type_names:
        return {"skipped": "no certified types"}
    certified = set(vocab.type_names)
    changes: Dict[str, str] = {}
    unmapped = 0
    with engine._read():
        for eid, ent in engine.entities.items():
            if ent.get("type") in certified:
                continue
            hit = vocab.types.get(key(ent.get("type", ""))) or vocab.types.get(key(ent.get("raw_type", "")))
            if hit:
                changes[eid] = hit
            else:
                unmapped += 1
    changed = engine.update_rows(entity_types=changes, actor=actor, action="compile.normalize_types")
    return {"updated": changed["entities"], "unmapped": unmapped}


def _normalize_predicates(engine: Any, run_id: str, actor: str) -> Dict[str, Any]:
    vocab = engine.ontology.vocabulary()
    if not vocab.predicate_names:
        return {"skipped": "no certified predicates"}
    certified = set(vocab.predicate_names)
    changes: Dict[str, Optional[str]] = {}
    with engine._read():
        for rid, rel in engine.relationships.items():
            if rel.get("predicate") in certified:
                continue
            hit = vocab.predicates.get(key(rel.get("predicate") or "")) or vocab.predicates.get(
                key(rel.get("description", ""))
            )
            if hit:
                changes[rid] = hit
    changed = engine.update_rows(predicates=changes, actor=actor, action="compile.normalize_predicates")
    return {"updated": changed["relationships"]}


def _merge_candidates(engine: Any, run_id: str, actor: str) -> Dict[str, Any]:
    groups: Dict[str, List[str]] = {}
    with engine._read():
        for eid, ent in engine.entities.items():
            canon = _canonical_name(ent["name"])
            if canon:
                groups.setdefault(canon, []).append(eid)
        candidates = []
        for canon, ids in groups.items():
            if len(ids) < 2:
                continue
            ids = sorted(ids)
            keep = max(ids, key=lambda i: (len(engine.entities[i].get("sources", [])), i))
            candidates.append(
                {
                    "canonical": canon,
                    "entity_ids": ids,
                    "names": [engine.entities[i]["name"] for i in ids],
                    "keep_id": keep,
                }
            )
    new = 0
    with engine.store.transaction():
        for cand in candidates[:_MAX_PER_STAGE]:
            new += _suggest(engine.store, run_id, "merge", "merge:" + "|".join(cand["entity_ids"]), cand)
    return {"candidates": len(candidates), "new_suggestions": new}


def _suggest_terms(engine: Any, run_id: str, actor: str) -> Dict[str, Any]:
    min_degree = int(os.getenv("VERITASGRAPH_TERM_MIN_DEGREE", "3"))
    conn = engine.store.conn
    linked = {r[0] for r in conn.execute("SELECT DISTINCT entity_id FROM term_entity")}
    existing = {r[0] for r in conn.execute("SELECT norm_name FROM term")}
    with engine._read():
        degree = _degree(engine)
        picks = [
            engine.entities[eid]
            for eid, d in sorted(degree.items(), key=lambda kv: -kv[1])
            if d >= min_degree and eid not in linked and key(engine.entities[eid]["name"]) not in existing
        ][:_MAX_PER_STAGE]
    new = 0
    with engine.store.transaction():
        for ent in picks:
            new += _suggest(
                engine.store,
                run_id,
                "term",
                f"term:{ent['id']}",
                {
                    "name": ent["name"],
                    "entity_id": ent["id"],
                    "type": ent.get("type"),
                    "definition": ent.get("description", ""),
                    "degree": degree[ent["id"]],
                },
            )
    return {"candidates": len(picks), "new_suggestions": new}


def _check_predicate_rules(engine: Any, run_id: str, actor: str) -> Dict[str, Any]:
    rules = engine.ontology.predicate_rules()
    if not rules:
        return {"skipped": "no certified predicates"}
    violations = []
    with engine._read():
        for rid, rel in engine.relationships.items():
            rule = rules.get(rel.get("predicate") or "")
            if not rule:
                continue
            s_type = engine.entities.get(rel["source"], {}).get("type")
            t_type = engine.entities.get(rel["target"], {}).get("type")
            problems = []
            if rule["domain_type"] and s_type != rule["domain_type"]:
                problems.append(f"source type '{s_type}' is not '{rule['domain_type']}'")
            if rule["range_type"] and t_type != rule["range_type"]:
                problems.append(f"target type '{t_type}' is not '{rule['range_type']}'")
            if problems:
                violations.append({"relationship_id": rid, "predicate": rel["predicate"], "problems": problems})
    new = 0
    with engine.store.transaction():
        for v in violations[:_MAX_PER_STAGE]:
            new += _suggest(engine.store, run_id, "violation", f"violation:{v['relationship_id']}:{v['predicate']}", v)
    return {"violations": len(violations), "new_suggestions": new}


def _detect_orphans(engine: Any, run_id: str, actor: str) -> Dict[str, Any]:
    with engine._read():
        degree = _degree(engine)
        orphans = [
            {"entity_id": eid, "name": engine.entities[eid]["name"]}
            for eid, d in degree.items()
            if d == 0 and eid in engine.entities
        ]
    new = 0
    with engine.store.transaction():
        for o in orphans[:_MAX_PER_STAGE]:
            new += _suggest(engine.store, run_id, "orphan", f"orphan:{o['entity_id']}", o)
    return {"orphans": len(orphans), "new_suggestions": new}


STAGES: List[tuple[str, Callable[[Any, str, str], Dict[str, Any]]]] = [
    ("normalize_types", _normalize_types),
    ("normalize_predicates", _normalize_predicates),
    ("merge_candidates", _merge_candidates),
    ("suggest_terms", _suggest_terms),
    ("check_predicate_rules", _check_predicate_rules),
    ("detect_orphans", _detect_orphans),
]


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #
def run_compile(engine: Any, *, trigger: str = "manual", actor: str = "system") -> Dict[str, Any]:
    """Run every stage once. Returns ``{"status": "busy"}`` if another process holds the lock."""
    store: Optional[SqliteGraphStore] = engine.store
    if store is None or engine.ontology is None:
        raise RuntimeError("Compile needs the shared store.")
    holder = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
    if not acquire_lock(store, LOCK_NAME, holder):
        return {"status": "busy"}
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    started = time.time()
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO compile_run(id, trigger, status, started_at) VALUES (?, ?, 'running', ?)",
            (run_id, trigger, started),
        )
    stages: List[Dict[str, Any]] = []
    status, error = "succeeded", None
    try:
        for name, fn in STAGES:
            t0 = time.time()
            result = fn(engine, run_id, actor)
            stages.append({"name": name, "seconds": round(time.time() - t0, 3), **result})
    except Exception as exc:  # noqa: BLE001 - recorded on the run, then re-raised
        status, error = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        with store.transaction() as conn:
            conn.execute(
                "UPDATE compile_run SET status = ?, finished_at = ?, graph_version = ?, stages = ?, "
                "error = ? WHERE id = ?",
                (status, time.time(), store.graph_version(), json.dumps(stages), error, run_id),
            )
            governance.record_audit(store, actor, "compile.run", run_id, {"trigger": trigger, "status": status})
        release_lock(store, LOCK_NAME, holder)
    return get_run(store, run_id) or {"id": run_id, "status": status}


def get_run(store: SqliteGraphStore, run_id: str) -> Optional[Dict[str, Any]]:
    row = store.conn.execute("SELECT * FROM compile_run WHERE id = ?", (run_id,)).fetchone()
    return {**dict(row), "stages": json.loads(row["stages"])} if row else None


def list_runs(store: SqliteGraphStore, limit: int = 20) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    rows = store.conn.execute("SELECT * FROM compile_run ORDER BY started_at DESC LIMIT ?", (limit,))
    return [{**dict(r), "stages": json.loads(r["stages"])} for r in rows]


def status(store: SqliteGraphStore) -> Dict[str, Any]:
    runs = list_runs(store, 1)
    open_counts = dict(
        store.conn.execute(
            "SELECT kind, COUNT(*) FROM suggestion WHERE status = 'open' GROUP BY kind"
        ).fetchall()
    )
    return {
        "last_run": runs[0] if runs else None,
        "open_suggestions": open_counts,
        "graph_version": store.graph_version(),
        "interval_seconds": interval_seconds(),
    }


def interval_seconds() -> int:
    try:
        return max(0, int(os.getenv("VERITASGRAPH_COMPILE_INTERVAL", "0")))
    except ValueError:
        return 0
