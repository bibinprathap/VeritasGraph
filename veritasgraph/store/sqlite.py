"""SQLite-backed graph store shared by the Studio and MCP processes.

Why SQLite: the previous JSON snapshot was rewritten in full on every change and
each process held its own copy, so two writers silently lost each other's work.
SQLite in WAL mode gives atomic multi-row writes, one writer at a time across
processes (``BEGIN IMMEDIATE``), and readers that never block.

Every write bumps ``meta.graph_version`` and stamps the rows it touched with that
version, so a process holding an in-memory cache can pull only what changed since
its last sync (:meth:`SqliteGraphStore.changes_since`). Destructive operations
(clear, restore) bump ``meta.epoch`` instead, telling caches to reload fully.

All SQL uses ``?`` placeholders; no value is ever interpolated into a statement.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from veritasgraph.store.migrations import MIGRATIONS

log = logging.getLogger(__name__)

KINDS = ("source", "entity", "relationship")

Rows = Dict[str, Dict[str, Any]]


def _norm(name: str) -> str:
    return " ".join((name or "").split()).lower()


def default_db_path(data_dir: Path) -> Path:
    """``VERITASGRAPH_DB`` wins; otherwise ``<data_dir>/veritasgraph.db``."""
    explicit = os.getenv("VERITASGRAPH_DB", "").strip()
    return Path(explicit) if explicit else data_dir / "veritasgraph.db"


class SqliteGraphStore:
    """Durable graph + governance storage. One connection per thread."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._migrate()

    # ------------------------------------------------------------------ #
    # Connections and transactions
    # ------------------------------------------------------------------ #
    @property
    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            # Autocommit mode: transactions are opened explicitly below.
            conn = sqlite3.connect(
                str(self.path), timeout=30.0, isolation_level=None, check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
            self._local.depth = 0
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Write transaction. Takes the database write lock up front so the
        read-modify-write inside cannot interleave with another process.
        Re-entrant within a thread (inner blocks join the outer transaction)."""
        conn = self.conn
        if self._local.depth:
            self._local.depth += 1
            try:
                yield conn
            finally:
                self._local.depth -= 1
            return
        conn.execute("BEGIN IMMEDIATE")
        self._local.depth = 1
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")
        finally:
            self._local.depth = 0

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        """Consistent multi-statement read snapshot (joins an open transaction)."""
        conn = self.conn
        if self._local.depth:
            yield conn
            return
        conn.execute("BEGIN")
        self._local.depth = 1
        try:
            yield conn
        finally:
            self._local.depth = 0
            conn.execute("COMMIT")

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def _migrate(self) -> None:
        with self.transaction() as conn:
            current = conn.execute("PRAGMA user_version").fetchone()[0]
            for index in range(current, len(MIGRATIONS)):
                for statement in _split_sql(MIGRATIONS[index]):
                    conn.execute(statement)
                # PRAGMA cannot take a parameter; the value is an int we control.
                conn.execute(f"PRAGMA user_version = {int(index + 1)}")
            if current < len(MIGRATIONS):
                log.info("veritasgraph store %s migrated to v%d", self.path, len(MIGRATIONS))

    def schema_version(self) -> int:
        return int(self.conn.execute("PRAGMA user_version").fetchone()[0])

    # ------------------------------------------------------------------ #
    # Meta
    # ------------------------------------------------------------------ #
    def get_meta(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def versions(self) -> Tuple[int, int]:
        """``(graph_version, epoch)`` in one round-trip."""
        rows = dict(
            self.conn.execute(
                "SELECT key, value FROM meta WHERE key IN ('graph_version', 'epoch')"
            ).fetchall()
        )
        return int(rows.get("graph_version", 0)), int(rows.get("epoch", 0))

    def graph_version(self) -> int:
        return self.versions()[0]

    def _bump(self, conn: sqlite3.Connection, *, epoch: bool = False) -> int:
        conn.execute(
            "UPDATE meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) "
            "WHERE key = 'graph_version'"
        )
        if epoch:
            conn.execute(
                "UPDATE meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) "
                "WHERE key = 'epoch'"
            )
        return int(
            conn.execute("SELECT value FROM meta WHERE key = 'graph_version'").fetchone()[0]
        )

    # ------------------------------------------------------------------ #
    # Graph rows
    # ------------------------------------------------------------------ #
    def load_all(self) -> Tuple[int, int, Rows, Rows, Rows]:
        with self.read() as conn:
            version, epoch = self.versions()
            sources = _bodies(conn.execute("SELECT body FROM source"))
            entities = _bodies(conn.execute("SELECT body FROM entity"))
            rels = _bodies(conn.execute("SELECT body FROM relationship"))
        return version, epoch, sources, entities, rels

    def changes_since(
        self, version: int
    ) -> Tuple[int, int, Dict[str, Rows], Dict[str, List[str]]]:
        """Rows written and ids deleted after ``version``."""
        with self.read() as conn:
            current, epoch = self.versions()
            upserts = {
                "source": _bodies(
                    conn.execute("SELECT body FROM source WHERE row_version > ?", (version,))
                ),
                "entity": _bodies(
                    conn.execute("SELECT body FROM entity WHERE row_version > ?", (version,))
                ),
                "relationship": _bodies(
                    conn.execute(
                        "SELECT body FROM relationship WHERE row_version > ?", (version,)
                    )
                ),
            }
            deleted: Dict[str, List[str]] = {k: [] for k in KINDS}
            for row in conn.execute(
                "SELECT kind, id FROM tombstone WHERE row_version > ?", (version,)
            ):
                deleted.setdefault(row["kind"], []).append(row["id"])
        return current, epoch, upserts, deleted

    def write_rows(
        self,
        *,
        sources: Iterable[Dict[str, Any]] = (),
        entities: Iterable[Dict[str, Any]] = (),
        relationships: Iterable[Dict[str, Any]] = (),
        deleted: Optional[Dict[str, Iterable[str]]] = None,
    ) -> int:
        """Upsert/delete rows and bump the graph version. Returns the new version."""
        with self.transaction() as conn:
            version = self._bump(conn)
            for src in sources:
                conn.execute(
                    "INSERT INTO source(id, doc_id, row_version, body) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET doc_id = excluded.doc_id, "
                    "row_version = excluded.row_version, body = excluded.body",
                    (src["id"], src.get("doc_id", ""), version, _dump(src)),
                )
                conn.execute("DELETE FROM tombstone WHERE kind = 'source' AND id = ?", (src["id"],))
            for ent in entities:
                conn.execute(
                    "INSERT INTO entity(id, norm_name, type, row_version, body) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET norm_name = excluded.norm_name, "
                    "type = excluded.type, row_version = excluded.row_version, "
                    "body = excluded.body",
                    (
                        ent["id"],
                        _norm(ent.get("name", "")),
                        ent.get("type", "concept"),
                        version,
                        _dump(ent),
                    ),
                )
                conn.execute("DELETE FROM tombstone WHERE kind = 'entity' AND id = ?", (ent["id"],))
            for rel in relationships:
                conn.execute(
                    "INSERT INTO relationship(id, source_id, target_id, predicate, "
                    "row_version, body) VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET source_id = excluded.source_id, "
                    "target_id = excluded.target_id, predicate = excluded.predicate, "
                    "row_version = excluded.row_version, body = excluded.body",
                    (
                        rel["id"],
                        rel["source"],
                        rel["target"],
                        rel.get("predicate"),
                        version,
                        _dump(rel),
                    ),
                )
                conn.execute(
                    "DELETE FROM tombstone WHERE kind = 'relationship' AND id = ?", (rel["id"],)
                )
            for kind, ids in (deleted or {}).items():
                if kind not in KINDS:
                    raise ValueError(f"Unknown row kind {kind!r}")
                for row_id in ids:
                    # ``kind`` is validated against KINDS, so the table name is safe.
                    conn.execute(f"DELETE FROM {kind} WHERE id = ?", (row_id,))
                    conn.execute(
                        "INSERT INTO tombstone(kind, id, row_version) VALUES (?, ?, ?) "
                        "ON CONFLICT(kind, id) DO UPDATE SET row_version = excluded.row_version",
                        (kind, row_id, version),
                    )
        return version

    def replace_graph(self, sources: Rows, entities: Rows, relationships: Rows) -> int:
        """Atomically replace the whole graph (clear / restore). Bumps the epoch."""
        with self.transaction() as conn:
            for kind in KINDS:
                conn.execute(f"DELETE FROM {kind}")  # constant table names
            conn.execute("DELETE FROM term_entity")
            conn.execute("DELETE FROM tombstone")
            self._bump(conn, epoch=True)
            if sources or entities or relationships:
                self.write_rows(
                    sources=sources.values(),
                    entities=entities.values(),
                    relationships=relationships.values(),
                )
            return self.graph_version()

    def counts(self) -> Dict[str, int]:
        conn = self.conn
        return {
            "sources": conn.execute("SELECT COUNT(*) FROM source").fetchone()[0],
            "entities": conn.execute("SELECT COUNT(*) FROM entity").fetchone()[0],
            "relationships": conn.execute("SELECT COUNT(*) FROM relationship").fetchone()[0],
        }

    def is_empty(self) -> bool:
        return not any(self.counts().values()) and self.graph_version() == 0


def _dump(row: Dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))


def _bodies(cursor: Iterable[sqlite3.Row]) -> Rows:
    out: Rows = {}
    for row in cursor:
        body = json.loads(row["body"])
        out[body["id"]] = body
    return out


def _split_sql(script: str) -> List[str]:
    """Split a migration into statements (no semicolons inside our literals)."""
    statements = []
    for part in script.split(";"):
        lines = [ln for ln in part.splitlines() if not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    return statements


_STORES: Dict[str, SqliteGraphStore] = {}
_STORES_LOCK = threading.Lock()


def open_store(path: Path | str) -> SqliteGraphStore:
    """Process-wide store per database path (so modules share connections)."""
    key = str(Path(path).resolve())
    with _STORES_LOCK:
        store = _STORES.get(key)
        if store is None:
            store = SqliteGraphStore(key)
            _STORES[key] = store
        return store
