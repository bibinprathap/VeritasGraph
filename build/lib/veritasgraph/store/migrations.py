"""Schema migrations for the VeritasGraph SQLite store.

Each entry is applied once, in order, inside a write transaction; the applied
count is tracked with ``PRAGMA user_version``. Never edit a migration that has
shipped — append a new one instead.
"""

from __future__ import annotations

from typing import List

MIGRATIONS: List[str] = [
    # 1 — core graph. Rows keep the full engine dict as JSON in ``body`` so no
    # field (origin, meta, provenance, flags) is lost; the indexed columns are
    # the ones queried directly. ``row_version`` is the graph_version of the last
    # write, which lets another process pull only what changed.
    """
    CREATE TABLE IF NOT EXISTS meta (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    INSERT OR IGNORE INTO meta(key, value) VALUES ('graph_version', '0');
    INSERT OR IGNORE INTO meta(key, value) VALUES ('epoch', '0');

    CREATE TABLE IF NOT EXISTS source (
        id          TEXT PRIMARY KEY,
        doc_id      TEXT NOT NULL,
        row_version INTEGER NOT NULL,
        body        TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_source_version ON source(row_version);
    CREATE INDEX IF NOT EXISTS ix_source_doc ON source(doc_id);

    CREATE TABLE IF NOT EXISTS entity (
        id          TEXT PRIMARY KEY,
        norm_name   TEXT NOT NULL UNIQUE,
        type        TEXT NOT NULL,
        row_version INTEGER NOT NULL,
        body        TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_entity_version ON entity(row_version);
    CREATE INDEX IF NOT EXISTS ix_entity_type ON entity(type);

    CREATE TABLE IF NOT EXISTS relationship (
        id          TEXT PRIMARY KEY,
        source_id   TEXT NOT NULL,
        target_id   TEXT NOT NULL,
        predicate   TEXT,
        row_version INTEGER NOT NULL,
        body        TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_rel_source ON relationship(source_id);
    CREATE INDEX IF NOT EXISTS ix_rel_target ON relationship(target_id);
    CREATE INDEX IF NOT EXISTS ix_rel_version ON relationship(row_version);

    -- Deletions, so other processes can drop rows from their caches.
    CREATE TABLE IF NOT EXISTS tombstone (
        kind        TEXT NOT NULL,
        id          TEXT NOT NULL,
        row_version INTEGER NOT NULL,
        PRIMARY KEY (kind, id)
    );
    CREATE INDEX IF NOT EXISTS ix_tombstone_version ON tombstone(row_version);
    """,
    # 2 — ontology: controlled vocabulary for entity types, predicates and a
    # business glossary of terms with synonyms, each with a certification status.
    """
    CREATE TABLE IF NOT EXISTS entity_type (
        name        TEXT PRIMARY KEY,
        description TEXT NOT NULL DEFAULT '',
        parent      TEXT,
        status      TEXT NOT NULL DEFAULT 'proposed'
                    CHECK (status IN ('proposed', 'certified', 'deprecated')),
        owner_id    TEXT,
        updated_at  REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS entity_type_synonym (
        type_name   TEXT NOT NULL REFERENCES entity_type(name) ON DELETE CASCADE,
        synonym     TEXT NOT NULL,
        PRIMARY KEY (type_name, synonym)
    );
    CREATE INDEX IF NOT EXISTS ix_type_synonym ON entity_type_synonym(synonym);

    CREATE TABLE IF NOT EXISTS predicate (
        name        TEXT PRIMARY KEY,
        description TEXT NOT NULL DEFAULT '',
        domain_type TEXT,
        range_type  TEXT,
        inverse     TEXT,
        status      TEXT NOT NULL DEFAULT 'proposed'
                    CHECK (status IN ('proposed', 'certified', 'deprecated')),
        owner_id    TEXT,
        updated_at  REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS predicate_synonym (
        predicate_name TEXT NOT NULL REFERENCES predicate(name) ON DELETE CASCADE,
        synonym        TEXT NOT NULL,
        PRIMARY KEY (predicate_name, synonym)
    );
    CREATE INDEX IF NOT EXISTS ix_predicate_synonym ON predicate_synonym(synonym);

    CREATE TABLE IF NOT EXISTS term (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        norm_name   TEXT NOT NULL UNIQUE,
        definition  TEXT NOT NULL DEFAULT '',
        status      TEXT NOT NULL DEFAULT 'proposed'
                    CHECK (status IN ('proposed', 'certified', 'deprecated')),
        owner_id    TEXT,
        updated_at  REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS term_synonym (
        term_id     TEXT NOT NULL REFERENCES term(id) ON DELETE CASCADE,
        synonym     TEXT NOT NULL,
        PRIMARY KEY (term_id, synonym)
    );
    CREATE INDEX IF NOT EXISTS ix_term_synonym ON term_synonym(synonym);
    CREATE TABLE IF NOT EXISTS term_entity (
        term_id     TEXT NOT NULL REFERENCES term(id) ON DELETE CASCADE,
        entity_id   TEXT NOT NULL,
        PRIMARY KEY (term_id, entity_id)
    );
    CREATE INDEX IF NOT EXISTS ix_term_entity_entity ON term_entity(entity_id);
    """,
    # 3 — compile pipeline, governance, answer receipts.
    """
    CREATE TABLE IF NOT EXISTS job_lock (
        name        TEXT PRIMARY KEY,
        holder      TEXT NOT NULL,
        expires_at  REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS compile_run (
        id          TEXT PRIMARY KEY,
        trigger     TEXT NOT NULL,
        status      TEXT NOT NULL,
        started_at  REAL NOT NULL,
        finished_at REAL,
        graph_version INTEGER,
        stages      TEXT NOT NULL DEFAULT '[]',
        error       TEXT
    );
    CREATE INDEX IF NOT EXISTS ix_compile_run_started ON compile_run(started_at);

    CREATE TABLE IF NOT EXISTS suggestion (
        id          TEXT PRIMARY KEY,
        kind        TEXT NOT NULL,
        fingerprint TEXT NOT NULL UNIQUE,
        status      TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'accepted', 'rejected')),
        run_id      TEXT,
        payload     TEXT NOT NULL,
        created_at  REAL NOT NULL,
        resolved_at REAL,
        resolved_by TEXT
    );
    CREATE INDEX IF NOT EXISTS ix_suggestion_status ON suggestion(status, kind);

    CREATE TABLE IF NOT EXISTS tag_rule (
        id          TEXT PRIMARY KEY,
        field       TEXT NOT NULL CHECK (field IN ('name', 'description', 'type')),
        pattern     TEXT NOT NULL,
        tag         TEXT NOT NULL,
        created_at  REAL NOT NULL
    );

    -- Append-only, hash-chained audit trail: each row's hash covers the
    -- previous row's hash, so any edit or deletion breaks verification.
    CREATE TABLE IF NOT EXISTS audit_event (
        seq         INTEGER PRIMARY KEY AUTOINCREMENT,
        ts          REAL NOT NULL,
        actor       TEXT NOT NULL,
        action      TEXT NOT NULL,
        target      TEXT NOT NULL DEFAULT '',
        detail      TEXT NOT NULL DEFAULT '{}',
        prev_hash   TEXT NOT NULL,
        hash        TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS snapshot (
        id            TEXT PRIMARY KEY,
        label         TEXT NOT NULL DEFAULT '',
        created_at    REAL NOT NULL,
        created_by    TEXT NOT NULL DEFAULT '',
        graph_version INTEGER NOT NULL,
        counts        TEXT NOT NULL DEFAULT '{}',
        body          BLOB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS answer_log (
        id            TEXT PRIMARY KEY,
        ts            REAL NOT NULL,
        actor         TEXT NOT NULL DEFAULT '',
        mode          TEXT NOT NULL,
        model         TEXT NOT NULL DEFAULT '',
        question      TEXT NOT NULL,
        answer        TEXT NOT NULL,
        grounded      INTEGER NOT NULL,
        abstained     INTEGER NOT NULL,
        graph_version INTEGER NOT NULL,
        evidence      TEXT NOT NULL DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS ix_answer_log_ts ON answer_log(ts);

    CREATE TABLE IF NOT EXISTS feedback (
        id          TEXT PRIMARY KEY,
        answer_id   TEXT NOT NULL REFERENCES answer_log(id) ON DELETE CASCADE,
        ts          REAL NOT NULL,
        actor       TEXT NOT NULL DEFAULT '',
        rating      INTEGER NOT NULL CHECK (rating IN (-1, 0, 1)),
        comment     TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS ix_feedback_answer ON feedback(answer_id);
    """,
]
