"""Ontology: a controlled vocabulary for the knowledge graph.

Three kinds of entry, each with a lifecycle ``proposed -> certified -> deprecated``:

* **entity types** (``organization``, ``person`` ...) with synonyms and a parent;
* **predicates** (``supplies``, ``owns`` ...) with optional domain/range types
  and an inverse;
* **terms** — a business glossary: a named concept with a definition, synonyms
  and links to the graph entities that embody it.

Editors propose; only admins certify (enforced by the Studio role check, and MCP
can only ever create ``proposed`` entries). Any edit to a certified entry sends it
back to ``proposed`` so a changed definition is never silently trusted.

Extraction uses :meth:`Ontology.vocabulary` to constrain the LLM and
:meth:`Vocabulary.resolve_type` / :meth:`Vocabulary.resolve_predicate` to map
whatever it returns onto certified names. With no certified vocabulary at all the
resolver is a pass-through, so a fresh install behaves exactly as before.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from veritasgraph.store.sqlite import SqliteGraphStore

STATUSES = ("proposed", "certified", "deprecated")
_KIND_TABLE = {"type": "entity_type", "predicate": "predicate"}
_MAX_NAME = 120
_MAX_TEXT = 4000


def key(text: str) -> str:
    """Comparison key: case-, whitespace-, underscore- and hyphen-insensitive."""
    return re.sub(r"[\s_\-]+", " ", (text or "").strip().lower()).strip()


def _clean_name(name: str) -> str:
    name = re.sub(r"\s+", " ", (name or "").strip())
    if not name:
        raise ValueError("name is required")
    if len(name) > _MAX_NAME:
        raise ValueError(f"name must be at most {_MAX_NAME} characters")
    return name


def _clean_text(text: Optional[str]) -> str:
    text = (text or "").strip()
    if len(text) > _MAX_TEXT:
        raise ValueError(f"text must be at most {_MAX_TEXT} characters")
    return text


def _clean_synonyms(synonyms: Optional[Iterable[str]]) -> List[str]:
    out: List[str] = []
    for syn in synonyms or []:
        k = key(str(syn))
        if k and k not in out and len(k) <= _MAX_NAME:
            out.append(k)
    return out


def _phrase_in(phrase: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


@dataclass
class Vocabulary:
    """A point-in-time view of the vocabulary, used during one extraction run."""

    types: Dict[str, str] = field(default_factory=dict)  # key -> certified type name
    predicates: Dict[str, str] = field(default_factory=dict)  # key -> certified predicate
    type_names: List[str] = field(default_factory=list)
    predicate_names: List[str] = field(default_factory=list)
    known_types: set = field(default_factory=set)  # keys of every non-deprecated entry
    known_predicates: set = field(default_factory=set)

    @property
    def constrained(self) -> bool:
        return bool(self.type_names or self.predicate_names)

    def resolve_type(self, raw: str) -> Tuple[str, Optional[str]]:
        """``(type, unmapped_raw)``. Unmapped values fall back to ``concept``."""
        cleaned = (raw or "").strip().lower() or "concept"
        if not self.type_names:
            return cleaned, None
        hit = self.types.get(key(cleaned))
        if hit:
            return hit, None
        return "concept", cleaned

    def resolve_predicate(self, raw: str) -> Tuple[Optional[str], Optional[str]]:
        """``(predicate, unmapped_raw)``. Without a vocabulary the raw value is kept."""
        k = key(raw)
        if not k:
            return None, None
        if not self.predicate_names:
            return k.replace(" ", "_"), None
        hit = self.predicates.get(k)
        if hit:
            return hit, None
        return None, k.replace(" ", "_")


class Ontology:
    def __init__(self, store: SqliteGraphStore) -> None:
        self.store = store

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def vocabulary(self) -> Vocabulary:
        conn = self.store.conn
        vocab = Vocabulary()
        for row in conn.execute("SELECT name, status FROM entity_type WHERE status != 'deprecated'"):
            vocab.known_types.add(key(row["name"]))
            if row["status"] == "certified":
                vocab.type_names.append(row["name"])
                vocab.types[key(row["name"])] = row["name"]
        for row in conn.execute(
            "SELECT s.synonym, t.name FROM entity_type_synonym s "
            "JOIN entity_type t ON t.name = s.type_name WHERE t.status = 'certified'"
        ):
            vocab.types.setdefault(key(row["synonym"]), row["name"])
        for row in conn.execute("SELECT name, status FROM predicate WHERE status != 'deprecated'"):
            vocab.known_predicates.add(key(row["name"]))
            if row["status"] == "certified":
                vocab.predicate_names.append(row["name"])
                vocab.predicates[key(row["name"])] = row["name"]
        for row in conn.execute(
            "SELECT s.synonym, p.name FROM predicate_synonym s "
            "JOIN predicate p ON p.name = s.predicate_name WHERE p.status = 'certified'"
        ):
            vocab.predicates.setdefault(key(row["synonym"]), row["name"])
        vocab.type_names.sort()
        vocab.predicate_names.sort()
        return vocab

    def snapshot(self) -> Dict[str, Any]:
        """The whole ontology, for the Studio tab and MCP."""
        conn = self.store.conn
        type_syn = _group(conn.execute("SELECT type_name, synonym FROM entity_type_synonym"))
        pred_syn = _group(conn.execute("SELECT predicate_name, synonym FROM predicate_synonym"))
        types = [
            {**dict(row), "synonyms": type_syn.get(row["name"], [])}
            for row in conn.execute("SELECT * FROM entity_type ORDER BY name")
        ]
        predicates = [
            {**dict(row), "synonyms": pred_syn.get(row["name"], [])}
            for row in conn.execute("SELECT * FROM predicate ORDER BY name")
        ]
        return {"types": types, "predicates": predicates, "terms": self.list_terms()}

    def list_terms(self, query: str = "", limit: int = 200) -> List[Dict[str, Any]]:
        conn = self.store.conn
        rows = conn.execute("SELECT * FROM term ORDER BY name").fetchall()
        syns = _group(conn.execute("SELECT term_id, synonym FROM term_synonym"))
        links = _group(conn.execute("SELECT term_id, entity_id FROM term_entity"))
        q = key(query)
        out = []
        for row in rows:
            synonyms = syns.get(row["id"], [])
            if q and q not in row["norm_name"] and not any(q in s for s in synonyms):
                continue
            out.append({**dict(row), "synonyms": synonyms, "entity_ids": links.get(row["id"], [])})
            if len(out) >= limit:
                break
        return out

    def get_term(self, term_id_or_name: str) -> Optional[Dict[str, Any]]:
        conn = self.store.conn
        row = conn.execute(
            "SELECT * FROM term WHERE id = ? OR norm_name = ?",
            (term_id_or_name, key(term_id_or_name)),
        ).fetchone()
        if row is None:
            return None
        synonyms = [
            r[0]
            for r in conn.execute(
                "SELECT synonym FROM term_synonym WHERE term_id = ? ORDER BY synonym", (row["id"],)
            )
        ]
        entity_ids = [
            r[0]
            for r in conn.execute(
                "SELECT entity_id FROM term_entity WHERE term_id = ? ORDER BY entity_id",
                (row["id"],),
            )
        ]
        return {**dict(row), "synonyms": synonyms, "entity_ids": entity_ids}

    def match_terms(self, text: str) -> List[Dict[str, Any]]:
        """Non-deprecated terms whose name or a synonym appears in ``text`` as a phrase."""
        q = key(text)
        if not q:
            return []
        matched = []
        for term in self.list_terms(limit=10_000):
            if term["status"] == "deprecated":
                continue
            phrases = [term["norm_name"], *term["synonyms"]]
            hits = [p for p in phrases if p and _phrase_in(p, q)]
            if hits:
                matched.append({**term, "matched": hits})
        return matched

    def terms_for_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        rows = self.store.conn.execute(
            "SELECT t.id, t.name, t.status FROM term t JOIN term_entity te ON te.term_id = t.id "
            "WHERE te.entity_id = ? ORDER BY t.name",
            (entity_id,),
        )
        return [dict(r) for r in rows]

    def predicate_rules(self) -> Dict[str, Dict[str, Any]]:
        rows = self.store.conn.execute(
            "SELECT name, domain_type, range_type FROM predicate WHERE status = 'certified'"
        )
        return {r["name"]: dict(r) for r in rows}

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #
    def upsert_type(
        self,
        name: str,
        *,
        description: str = "",
        parent: Optional[str] = None,
        synonyms: Optional[Iterable[str]] = None,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        name = key(_clean_name(name))
        description = _clean_text(description)
        parent = key(parent) if parent else None
        if parent == name:
            raise ValueError("a type cannot be its own parent")
        syns = [s for s in _clean_synonyms(synonyms) if s != name]
        with self.store.transaction() as conn:
            if parent and not conn.execute(
                "SELECT 1 FROM entity_type WHERE name = ?", (parent,)
            ).fetchone():
                raise ValueError(f"unknown parent type '{parent}'")
            conn.execute(
                "INSERT INTO entity_type(name, description, parent, status, owner_id, updated_at) "
                "VALUES (?, ?, ?, 'proposed', ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET description = excluded.description, "
                "parent = excluded.parent, status = 'proposed', "
                "owner_id = COALESCE(excluded.owner_id, entity_type.owner_id), "
                "updated_at = excluded.updated_at",
                (name, description, parent, owner_id, time.time()),
            )
            conn.execute("DELETE FROM entity_type_synonym WHERE type_name = ?", (name,))
            conn.executemany(
                "INSERT INTO entity_type_synonym(type_name, synonym) VALUES (?, ?)",
                [(name, s) for s in syns],
            )
        return self._get("type", name)

    def upsert_predicate(
        self,
        name: str,
        *,
        description: str = "",
        domain_type: Optional[str] = None,
        range_type: Optional[str] = None,
        inverse: Optional[str] = None,
        synonyms: Optional[Iterable[str]] = None,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        name = key(_clean_name(name)).replace(" ", "_")
        description = _clean_text(description)
        domain_type = key(domain_type) if domain_type else None
        range_type = key(range_type) if range_type else None
        inverse = key(inverse).replace(" ", "_") if inverse else None
        syns = [s for s in _clean_synonyms(synonyms) if s != key(name)]
        with self.store.transaction() as conn:
            for t in (domain_type, range_type):
                if t and not conn.execute("SELECT 1 FROM entity_type WHERE name = ?", (t,)).fetchone():
                    raise ValueError(f"unknown entity type '{t}'")
            conn.execute(
                "INSERT INTO predicate(name, description, domain_type, range_type, inverse, "
                "status, owner_id, updated_at) VALUES (?, ?, ?, ?, ?, 'proposed', ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET description = excluded.description, "
                "domain_type = excluded.domain_type, range_type = excluded.range_type, "
                "inverse = excluded.inverse, status = 'proposed', "
                "owner_id = COALESCE(excluded.owner_id, predicate.owner_id), "
                "updated_at = excluded.updated_at",
                (name, description, domain_type, range_type, inverse, owner_id, time.time()),
            )
            conn.execute("DELETE FROM predicate_synonym WHERE predicate_name = ?", (name,))
            conn.executemany(
                "INSERT INTO predicate_synonym(predicate_name, synonym) VALUES (?, ?)",
                [(name, s) for s in syns],
            )
        return self._get("predicate", name)

    def upsert_term(
        self,
        name: str,
        *,
        definition: str = "",
        synonyms: Optional[Iterable[str]] = None,
        entity_ids: Optional[Iterable[str]] = None,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a glossary term (always lands as ``proposed``)."""
        name = _clean_name(name)
        norm = key(name)
        definition = _clean_text(definition)
        syns = [s for s in _clean_synonyms(synonyms) if s != norm]
        with self.store.transaction() as conn:
            row = conn.execute("SELECT id FROM term WHERE norm_name = ?", (norm,)).fetchone()
            term_id = row["id"] if row else f"term_{uuid.uuid4().hex[:10]}"
            conn.execute(
                "INSERT INTO term(id, name, norm_name, definition, status, owner_id, updated_at) "
                "VALUES (?, ?, ?, ?, 'proposed', ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name = excluded.name, "
                "definition = excluded.definition, status = 'proposed', "
                "owner_id = COALESCE(excluded.owner_id, term.owner_id), "
                "updated_at = excluded.updated_at",
                (term_id, name, norm, definition, owner_id, time.time()),
            )
            conn.execute("DELETE FROM term_synonym WHERE term_id = ?", (term_id,))
            conn.executemany(
                "INSERT INTO term_synonym(term_id, synonym) VALUES (?, ?)",
                [(term_id, s) for s in syns],
            )
            if entity_ids is not None:
                conn.execute("DELETE FROM term_entity WHERE term_id = ?", (term_id,))
                self._link(conn, term_id, entity_ids)
            # Auto-link entities whose name is the term or one of its synonyms.
            for phrase in [norm, *syns]:
                for ent in conn.execute(
                    "SELECT id FROM entity WHERE norm_name = ?", (phrase,)
                ).fetchall():
                    conn.execute(
                        "INSERT OR IGNORE INTO term_entity(term_id, entity_id) VALUES (?, ?)",
                        (term_id, ent["id"]),
                    )
        term = self.get_term(term_id)
        assert term is not None
        return term

    def link_entities(self, term_id: str, entity_ids: Iterable[str]) -> Dict[str, Any]:
        with self.store.transaction() as conn:
            if not conn.execute("SELECT 1 FROM term WHERE id = ?", (term_id,)).fetchone():
                raise KeyError(term_id)
            self._link(conn, term_id, entity_ids)
        term = self.get_term(term_id)
        assert term is not None
        return term

    @staticmethod
    def _link(conn: Any, term_id: str, entity_ids: Iterable[str]) -> None:
        for eid in entity_ids:
            if not conn.execute("SELECT 1 FROM entity WHERE id = ?", (eid,)).fetchone():
                raise ValueError(f"unknown entity '{eid}'")
            conn.execute(
                "INSERT OR IGNORE INTO term_entity(term_id, entity_id) VALUES (?, ?)",
                (term_id, eid),
            )

    def set_status(self, kind: str, ident: str, status: str) -> Dict[str, Any]:
        """Certify or deprecate an entry. Callers enforce the admin role."""
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        if kind == "term":
            table, column = "term", "id"
        elif kind in _KIND_TABLE:
            table, column = _KIND_TABLE[kind], "name"
        else:
            raise ValueError("kind must be type, predicate or term")
        with self.store.transaction() as conn:
            # table/column come from the fixed mapping above, never from input.
            cur = conn.execute(
                f"UPDATE {table} SET status = ?, updated_at = ? WHERE {column} = ?",
                (status, time.time(), ident),
            )
            if cur.rowcount == 0:
                raise KeyError(ident)
        return self.get_term(ident) if kind == "term" else self._get(kind, ident)  # type: ignore[return-value]

    def record_proposals(self, types: Iterable[str], predicates: Iterable[str]) -> None:
        """Remember unmapped extraction output as ``proposed`` entries for review."""
        now = time.time()
        with self.store.transaction() as conn:
            for t in {key(x) for x in types if x}:
                if t and len(t) <= _MAX_NAME:
                    conn.execute(
                        "INSERT OR IGNORE INTO entity_type(name, description, status, owner_id, "
                        "updated_at) VALUES (?, 'Seen in extraction output', 'proposed', "
                        "'extraction', ?)",
                        (t, now),
                    )
            for p in {key(x).replace(" ", "_") for x in predicates if x}:
                if p and len(p) <= _MAX_NAME:
                    conn.execute(
                        "INSERT OR IGNORE INTO predicate(name, description, status, owner_id, "
                        "updated_at) VALUES (?, 'Seen in extraction output', 'proposed', "
                        "'extraction', ?)",
                        (p, now),
                    )

    def _get(self, kind: str, name: str) -> Dict[str, Any]:
        snap = self.snapshot()
        items = snap["types"] if kind == "type" else snap["predicates"]
        for item in items:
            if item["name"] == name:
                return item
        raise KeyError(name)


def _group(rows: Iterable[Any]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for a, b in rows:
        out.setdefault(a, []).append(b)
    return out
