"""VeritasGraph-style GraphRAG engine for the studio.

This is a self-contained, local implementation of the core VeritasGraph ideas:

* **Knowledge graph construction** — a document is split into source chunks and a
  local LLM extracts entities and relationships from each chunk. Every node and
  edge records which source chunk it came from, which is what makes attribution
  *verifiable*.
* **Multi-hop retrieval** — a query is matched to seed entities, then the graph
  is expanded outward (breadth-first, bounded depth) to gather a relevant
  subgraph, mirroring VeritasGraph's "reason based on structure" retrieval.
* **Grounded answers with citations** — the subgraph plus the originating source
  chunks are handed to the LLM, which must answer using only that context and
  cite the source ids it relied on.

Storage: the graph lives in a SQLite database shared by every process (Studio,
MCP, CLI) — see :mod:`veritasgraph.store`. The engine keeps the graph in
in-memory dicts as a read cache, re-syncs it whenever another process has
written (``graph_version`` changed), and persists only the rows it changed in
one ``BEGIN IMMEDIATE`` transaction. A legacy ``knowledge_graph.json`` is
migrated automatically on first start.

Subclasses that override :meth:`GraphRAGEngine._load` (e.g. the evaluation
harness) opt out of the database and keep pure in-memory behaviour.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import httpx

from veritasgraph import governance, pii
from veritasgraph.ontology import Ontology, Vocabulary
from veritasgraph.ontology import key as onto_key
from veritasgraph.store.migrate_json import migrate_json
from veritasgraph.store.sqlite import SqliteGraphStore, default_db_path, open_store
from veritasgraph.text import norm as norm_text
from veritasgraph.text import query_tokens as _query_tokens

log = logging.getLogger(__name__)

_DATA_DIR = Path(
    os.getenv("STUDIO_DATA_DIR", str(Path(__file__).resolve().parent / "data"))
)
_GRAPH_SNAPSHOT = _DATA_DIR / "knowledge_graph.json"

# Source ids look like "doc_<hex>#<n>" (ingest) or "imp_<hex>#<n>" (import);
# callers such as the eval harness may use other "<prefix>_<id>#<n>" forms.
_SOURCE_ID_RE = re.compile(r"(?<![\w#])([A-Za-z][A-Za-z0-9]*_[A-Za-z0-9]+#\d+)")

# Roughly characters per source chunk during ingestion.
_CHUNK_SIZE = int(os.getenv("STUDIO_GRAPH_CHUNK_SIZE", "1200"))


def _ollama_base() -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    if not host.startswith("http"):
        host = f"http://{host}"
    return host.rstrip("/")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _norm(name: str) -> str:
    """Normalise an entity name for de-duplication."""
    return norm_text(name)


def _chunk_text(text: str, size: int = _CHUNK_SIZE) -> List[str]:
    """Split text into chunks on paragraph boundaries where possible."""
    text = text.strip()
    if not text:
        return []
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            # A single huge paragraph is hard-split.
            while len(para) > size:
                chunks.append(para[:size])
                para = para[size:]
            current = para
    if current:
        chunks.append(current)
    return chunks


_EXTRACTION_SYSTEM = (
    "You are a knowledge-graph extraction engine. From the given text you extract "
    "entities and the relationships between them. Respond with STRICT JSON only, "
    "no prose, using this schema:\n"
    '{"entities": [{"name": "...", "type": "...", "description": "..."}], '
    '"relationships": [{"source": "...", "target": "...", "description": "..."}]}\n'
    "Rules: entity 'type' is a short category like person, organization, concept, "
    "product, location, event. 'source' and 'target' in relationships MUST be "
    "entity names that appear in the entities list. Keep descriptions concise. "
    "If nothing is present, return empty arrays."
)

# Used once an ontology has certified vocabulary: constrains types and asks for
# a typed predicate on each relationship.
_GUIDED_EXTRACTION_SYSTEM = (
    "You are a knowledge-graph extraction engine. From the given text you extract "
    "entities and the relationships between them. Respond with STRICT JSON only, "
    "no prose, using this schema:\n"
    '{{"entities": [{{"name": "...", "type": "...", "description": "..."}}], '
    '"relationships": [{{"source": "...", "target": "...", "predicate": "...", '
    '"description": "..."}}]}}\n'
    "Rules: entity 'type' MUST be one of: {types}. Use 'concept' if none fits. "
    "Relationship 'predicate' MUST be one of: {predicates}. Leave it empty if none "
    "fits and describe the relation in 'description'. 'source' and 'target' MUST "
    "be entity names that appear in the entities list. Keep descriptions concise. "
    "If nothing is present, return empty arrays."
)


def extraction_prompt(vocab: Optional[Vocabulary]) -> str:
    """The extraction system prompt; unchanged when no vocabulary is certified."""
    if vocab is None or not vocab.constrained:
        return _EXTRACTION_SYSTEM
    return _GUIDED_EXTRACTION_SYSTEM.format(
        types=", ".join(vocab.type_names) or "any short category",
        predicates=", ".join(vocab.predicate_names) or "any short verb phrase",
    )


def _extract_json(text: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response."""
    if not text:
        return {}
    # Strip code fences.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        candidate = text[start : end + 1] if start != -1 and end != -1 else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


# --------------------------------------------------------------------------- #
# Provenance + import adapters
#
# Nodes and edges carry a ``source_type`` recording how they entered the graph:
#   * "curated"   — imported from a human-reviewed graph (authoritative).
#   * "extracted" — produced by the document-extraction pipeline.
#   * "inferred"  — suggested/completed by an LLM (lowest confidence).
# On a merge conflict the higher-ranked provenance wins so that curated content
# is never silently overwritten by extracted or inferred data.
# --------------------------------------------------------------------------- #
_PROVENANCE_RANK: Dict[str, int] = {"curated": 3, "extracted": 2, "inferred": 1}
_DEFAULT_SOURCE_TYPE = "extracted"


def _provenance_rank(source_type: Optional[str]) -> int:
    return _PROVENANCE_RANK.get((source_type or _DEFAULT_SOURCE_TYPE), 0)


def _first(mapping: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-empty value for any of ``keys``."""
    for key in keys:
        if key in mapping and mapping[key] not in (None, "", [], {}):
            return mapping[key]
    return default


def _detect_format(graph: Dict[str, Any]) -> str:
    """Best-effort detection of the uploaded graph's source format."""
    if not isinstance(graph, dict):
        return "generic"
    # Understand-Anything: a KnowledgeGraph with project metadata + edges/tour.
    if isinstance(graph.get("project"), dict) and (
        "tour" in graph or "layers" in graph or "edges" in graph
    ):
        return "understand_anything"
    # Graphify: networkx node-link export uses "links" and node-link flags.
    if "links" in graph and ("nodes" in graph):
        if "directed" in graph or "multigraph" in graph or "hyperedges" in graph:
            return "graphify"
        return "graphify"
    return "generic"


def _adapt_graphify(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a Graphify ``graph.json`` (networkx node-link) export."""
    nodes: List[Dict[str, Any]] = []
    for raw in graph.get("nodes", []) or []:
        if not isinstance(raw, dict):
            continue
        origin_id = raw.get("id")
        name = _first(raw, "label", "name", "id", default=origin_id)
        if origin_id is None or name is None:
            continue
        meta = {
            k: v
            for k, v in raw.items()
            if k not in ("id", "label", "name", "type", "file_type",
                         "summary", "description", "norm_label")
            and not k.startswith("_")
        }
        nodes.append({
            "origin_id": str(origin_id),
            "name": str(name),
            "type": _first(raw, "file_type", "type", "community_name", default="concept"),
            "description": _first(raw, "summary", "description", default=""),
            "meta": meta,
        })
    edges: List[Dict[str, Any]] = []
    for raw in graph.get("links", []) or graph.get("edges", []) or []:
        if not isinstance(raw, dict):
            continue
        src = raw.get("source")
        tgt = raw.get("target")
        if src is None or tgt is None:
            continue
        edges.append({
            "source": str(src),
            "target": str(tgt),
            "description": _first(raw, "relation", "label", "type", "description", default=""),
        })
    return {
        "nodes": nodes,
        "edges": edges,
        "format": "graphify",
        "title": None,
        "version": graph.get("built_at_commit"),
    }


def _adapt_understand_anything(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise an Understand-Anything ``KnowledgeGraph`` export."""
    project = graph.get("project") if isinstance(graph.get("project"), dict) else {}
    nodes: List[Dict[str, Any]] = []
    for raw in graph.get("nodes", []) or []:
        if not isinstance(raw, dict):
            continue
        origin_id = raw.get("id")
        name = _first(raw, "name", "id", default=origin_id)
        if origin_id is None or name is None:
            continue
        meta = {
            k: v
            for k, v in raw.items()
            if k in ("filePath", "lineRange", "tags", "complexity",
                     "languageNotes", "domainMeta", "knowledgeMeta", "figmaMeta")
            and v not in (None, "", [], {})
        }
        nodes.append({
            "origin_id": str(origin_id),
            "name": str(name),
            "type": _first(raw, "type", default="concept"),
            "description": _first(raw, "summary", "description", default=""),
            "meta": meta,
        })
    edges: List[Dict[str, Any]] = []
    for raw in graph.get("edges", []) or graph.get("links", []) or []:
        if not isinstance(raw, dict):
            continue
        src = raw.get("source")
        tgt = raw.get("target")
        if src is None or tgt is None:
            continue
        desc = _first(raw, "description", "type", default="")
        edges.append({
            "source": str(src),
            "target": str(tgt),
            "description": str(desc),
        })
    return {
        "nodes": nodes,
        "edges": edges,
        "format": "understand_anything",
        "title": project.get("name"),
        "summary": project.get("description"),
        "version": _first(project, "gitCommitHash", "analyzedAt") or graph.get("version"),
    }


def _adapt_generic(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise an arbitrary JSON graph (e.g. AI Atlas taxonomy).

    Accepts nodes under ``nodes``/``entities``/``concepts`` and edges under
    ``edges``/``links``/``relationships``/``relations``. Endpoint keys are
    auto-detected (source/target, from/to, subject/object, parent/child).
    Hierarchical taxonomies that only express ``parent``/``parentId``/``children``
    on nodes are converted into ``categorized_under`` edges.
    """
    raw_nodes = _first(graph, "nodes", "entities", "concepts", "items", default=[])
    raw_edges = _first(
        graph, "edges", "links", "relationships", "relations", default=[]
    )
    if not isinstance(raw_nodes, list):
        raw_nodes = []
    if not isinstance(raw_edges, list):
        raw_edges = []

    nodes: List[Dict[str, Any]] = []
    seen_ids: set = set()
    synthesized_edges: List[Dict[str, Any]] = []
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            continue
        origin_id = _first(raw, "id", "key", "slug", "name", "title")
        name = _first(raw, "name", "label", "title", "id", default=origin_id)
        if origin_id is None or name is None:
            continue
        origin_id = str(origin_id)
        seen_ids.add(origin_id)
        reserved = {"id", "key", "slug", "name", "label", "title", "type",
                    "category", "kind", "description", "summary", "definition",
                    "content", "parent", "parentId", "parent_id", "children"}
        meta = {k: v for k, v in raw.items()
                if k not in reserved and v not in (None, "", [], {})}
        nodes.append({
            "origin_id": origin_id,
            "name": str(name),
            "type": _first(raw, "type", "category", "kind", default="concept"),
            "description": _first(raw, "description", "summary", "definition", "content", default=""),
            "meta": meta,
        })
        # Hierarchy expressed on the node itself.
        parent = _first(raw, "parent", "parentId", "parent_id")
        if parent is not None:
            synthesized_edges.append({
                "source": origin_id,
                "target": str(parent),
                "description": "categorized_under",
            })
        for child in raw.get("children", []) or []:
            child_id = child.get("id") if isinstance(child, dict) else child
            if child_id is not None:
                synthesized_edges.append({
                    "source": str(child_id),
                    "target": origin_id,
                    "description": "categorized_under",
                })

    edges: List[Dict[str, Any]] = []
    for raw in raw_edges:
        if not isinstance(raw, dict):
            continue
        src = _first(raw, "source", "from", "subject", "child", "start", "src")
        tgt = _first(raw, "target", "to", "object", "parent", "end", "dst")
        if src is None or tgt is None:
            continue
        edges.append({
            "source": str(src),
            "target": str(tgt),
            "description": str(_first(
                raw, "relation", "type", "label", "description", "predicate", default=""
            )),
        })
    edges.extend(synthesized_edges)
    return {
        "nodes": nodes,
        "edges": edges,
        "format": "generic",
        "title": _first(graph, "name", "title"),
        "summary": _first(graph, "description", "summary"),
        "version": _first(graph, "version", "revision"),
    }


_FORMAT_ADAPTERS = {
    "graphify": _adapt_graphify,
    "understand_anything": _adapt_understand_anything,
    "understand-anything": _adapt_understand_anything,
    "ua": _adapt_understand_anything,
    "ai_atlas": _adapt_generic,
    "ai-atlas": _adapt_generic,
    "generic": _adapt_generic,
    "json": _adapt_generic,
}


class GraphRAGEngine:
    """Owns the knowledge graph: sources, entities, relationships."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.relationships: Dict[str, Dict[str, Any]] = {}
        # Fast lookup from normalised entity name -> entity id.
        self._name_index: Dict[str, str] = {}
        # (source_eid, target_eid) -> relationship id; rebuilt lazily.
        self._rel_index: Dict[Tuple[str, str], str] = {}
        # Extra Ollama options (e.g. temperature) and request timeout.
        self.chat_options: Dict[str, Any] = {}
        self.chat_timeout: float = 180.0
        # Shared store; None for subclasses that manage their own persistence.
        self.store: Optional[SqliteGraphStore] = None
        self.ontology: Optional[Ontology] = None
        self._version = -1
        self._epoch = -1
        self._dirty: Dict[str, set] = {"source": set(), "entity": set(), "relationship": set()}
        self._deleted: Dict[str, set] = {"source": set(), "entity": set(), "relationship": set()}
        if type(self)._load is GraphRAGEngine._load:
            self.store = open_store(default_db_path(_DATA_DIR))
            self.ontology = Ontology(self.store)
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        store = self.store
        if store is None:
            return
        if store.is_empty() and _GRAPH_SNAPSHOT.is_file():
            try:
                report = migrate_json(_GRAPH_SNAPSHOT, store)
                log.info("Migrated %s into %s: %s", _GRAPH_SNAPSHOT, store.path, report)
            except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
                log.warning("Could not migrate %s: %s", _GRAPH_SNAPSHOT, exc)
        self._reload_all()

    def _reload_all(self) -> None:
        assert self.store is not None
        version, epoch, sources, entities, rels = self.store.load_all()
        self.sources, self.entities, self.relationships = sources, entities, rels
        self._name_index = {_norm(e["name"]): eid for eid, e in self.entities.items()}
        self._rel_index = {}
        self._version, self._epoch = version, epoch
        self._clear_dirty()

    def _sync(self) -> None:
        """Pull writes made by other processes since our last sync."""
        store = self.store
        if store is None:
            return
        version, epoch = store.versions()
        if epoch != self._epoch:
            self._reload_all()
            return
        if version == self._version:
            return
        version, epoch, upserts, deleted = store.changes_since(self._version)
        if epoch != self._epoch:
            self._reload_all()
            return
        self.sources.update(upserts["source"])
        for eid, ent in upserts["entity"].items():
            self.entities[eid] = ent
            self._name_index[_norm(ent["name"])] = eid
        self.relationships.update(upserts["relationship"])
        for sid in deleted.get("source", []):
            self.sources.pop(sid, None)
        for eid in deleted.get("entity", []):
            ent = self.entities.pop(eid, None)
            if ent is not None and self._name_index.get(_norm(ent["name"])) == eid:
                del self._name_index[_norm(ent["name"])]
        for rid in deleted.get("relationship", []):
            self.relationships.pop(rid, None)
        self._rel_index = {}
        self._version = version

    def _mark(self, kind: str, row_id: str) -> None:
        self._dirty[kind].add(row_id)
        self._deleted[kind].discard(row_id)

    def _mark_deleted(self, kind: str, row_id: str) -> None:
        self._deleted[kind].add(row_id)
        self._dirty[kind].discard(row_id)

    def _clear_dirty(self) -> None:
        for kind in self._dirty:
            self._dirty[kind].clear()
            self._deleted[kind].clear()

    def _flush(self) -> None:
        """Write dirty rows to the store (caller holds a store transaction)."""
        assert self.store is not None
        if not any(self._dirty.values()) and not any(self._deleted.values()):
            return
        self._version = self.store.write_rows(
            sources=[self.sources[i] for i in self._dirty["source"] if i in self.sources],
            entities=[self.entities[i] for i in self._dirty["entity"] if i in self.entities],
            relationships=[
                self.relationships[i] for i in self._dirty["relationship"] if i in self.relationships
            ],
            deleted={k: list(v) for k, v in self._deleted.items() if v},
        )
        self._clear_dirty()

    def _save(self) -> None:
        """Persist pending changes (kept for subclasses/older callers)."""
        if self.store is None:
            return
        with self._lock, self.store.transaction():
            self._flush()

    @contextmanager
    def _write(self) -> Iterator[None]:
        """Serialise a mutation across threads *and* processes.

        Inside the block the cache is up to date with the database and nobody
        else can write; on success the dirty rows are committed atomically, on
        failure the database rolls back and the cache is reloaded from it.
        """
        with self._lock:
            if self.store is None:
                yield
                self._save()
                return
            try:
                with self.store.transaction():
                    self._sync()
                    yield
                    self._flush()
            except BaseException:
                self._reload_all()
                raise

    @contextmanager
    def _read(self) -> Iterator[None]:
        with self._lock:
            self._sync()
            yield

    @property
    def graph_version(self) -> int:
        if self.store is None:
            return 0
        with self._read():
            return self._version

    def _audit(self, actor: str, action: str, target: str = "", detail: Optional[Dict[str, Any]] = None) -> None:
        if self.store is not None:
            governance.record_audit(self.store, actor or "system", action, target, detail)

    def _vocabulary(self) -> Optional[Vocabulary]:
        return self.ontology.vocabulary() if self.ontology is not None else None

    # ------------------------------------------------------------------ #
    # LLM access
    # ------------------------------------------------------------------ #
    def _chat(self, model: str, messages: List[Dict[str, str]]) -> str:
        if os.environ.get("VG_GRAPHRAG_CHAT", "").strip().lower() == "openai":
            from dataclasses import replace

            from veritasgraph.llm import ChatClient, endpoint

            client = ChatClient(replace(endpoint("fast"), model=model or endpoint("fast").model))
            try:
                return client.complete(messages)
            finally:
                client.close()
        url = f"{_ollama_base()}/api/chat"
        body: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if self.chat_options:
            body["options"] = dict(self.chat_options)
        with httpx.Client(timeout=self.chat_timeout) as client:
            resp = client.post(url, json=body)
            resp.raise_for_status()
            result = resp.json()
        return (result.get("message") or {}).get("content", "")

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #
    def _upsert_entity(
        self,
        name: str,
        etype: str,
        description: str,
        source_id: str,
        *,
        source_type: str = _DEFAULT_SOURCE_TYPE,
        origin: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
        pii_flags: Optional[List[str]] = None,
    ) -> Optional[str]:
        key = _norm(name)
        if not key:
            return None
        eid = self._name_index.get(key)
        if eid is None:
            eid = _new_id("ent")
            entity = {
                "id": eid,
                "name": name.strip(),
                "type": (etype or "concept").strip().lower(),
                "description": (description or "").strip(),
                "sources": [source_id],
                "source_type": source_type,
            }
            if origin:
                entity["origin"] = origin
            if pii_flags:
                entity["pii_flags"] = sorted(set(pii_flags))
            self.entities[eid] = entity
            self._name_index[key] = eid
        else:
            entity = self.entities[eid]
            if source_id not in entity["sources"]:
                entity["sources"].append(source_id)
            if pii_flags:
                entity["pii_flags"] = sorted(set(entity.get("pii_flags", [])) | set(pii_flags))
            new_rank = _provenance_rank(source_type)
            old_rank = _provenance_rank(entity.get("source_type"))
            incoming_desc = (description or "").strip()
            if overwrite or new_rank > old_rank:
                # Authoritative incoming data replaces existing fields.
                if etype:
                    entity["type"] = etype.strip().lower()
                if incoming_desc:
                    entity["description"] = incoming_desc
                entity["source_type"] = source_type
                if origin:
                    entity["origin"] = origin
            elif new_rank == old_rank and incoming_desc and len(incoming_desc) > len(
                entity.get("description", "")
            ):
                # Same provenance tier: keep the richer description.
                entity["description"] = incoming_desc
        self._mark("entity", eid)
        return eid

    def _find_relationship(self, source_eid: str, target_eid: str) -> Optional[str]:
        if len(self._rel_index) != len(self.relationships):
            self._rel_index = {
                (rel["source"], rel["target"]): rid
                for rid, rel in self.relationships.items()
            }
        rid = self._rel_index.get((source_eid, target_eid))
        if rid is not None and rid in self.relationships:
            return rid
        return None

    def _upsert_relationship(
        self,
        source_eid: str,
        target_eid: str,
        description: str,
        source_id: str,
        *,
        source_type: str = _DEFAULT_SOURCE_TYPE,
        origin: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
        predicate: Optional[str] = None,
        pii_flags: Optional[List[str]] = None,
    ) -> None:
        rid = self._find_relationship(source_eid, target_eid)
        if rid is not None:
            rel = self.relationships[rid]
            if source_id not in rel["sources"]:
                rel["sources"].append(source_id)
            if pii_flags:
                rel["pii_flags"] = sorted(set(rel.get("pii_flags", [])) | set(pii_flags))
            new_rank = _provenance_rank(source_type)
            old_rank = _provenance_rank(rel.get("source_type"))
            incoming_desc = (description or "").strip()
            if predicate and (not rel.get("predicate") or overwrite or new_rank > old_rank):
                rel["predicate"] = predicate
            if overwrite or new_rank > old_rank:
                if incoming_desc:
                    rel["description"] = incoming_desc
                rel["source_type"] = source_type
                if origin:
                    rel["origin"] = origin
            elif new_rank == old_rank and incoming_desc and len(incoming_desc) > len(
                rel.get("description", "")
            ):
                rel["description"] = incoming_desc
            self._mark("relationship", rid)
            return
        rid = _new_id("rel")
        rel = {
            "id": rid,
            "source": source_eid,
            "target": target_eid,
            "description": (description or "").strip(),
            "sources": [source_id],
            "source_type": source_type,
        }
        if predicate:
            rel["predicate"] = predicate
        if origin:
            rel["origin"] = origin
        if pii_flags:
            rel["pii_flags"] = sorted(set(pii_flags))
        self.relationships[rid] = rel
        self._rel_index[(source_eid, target_eid)] = rid
        self._mark("relationship", rid)

    def extract_chunk(
        self, chunk: str, model: str, *, vocab: Optional[Vocabulary] = None
    ) -> Dict[str, Any]:
        """Run LLM extraction on one chunk. Thread-safe: touches no graph state.

        With a certified ontology the prompt constrains entity types and asks
        for a predicate per relationship; otherwise the prompt is unchanged.
        """
        if vocab is None:
            vocab = self._vocabulary()
        raw = self._chat(
            model,
            [
                {"role": "system", "content": extraction_prompt(vocab)},
                {"role": "user", "content": chunk},
            ],
        )
        return _extract_json(raw)

    def merge_chunk(
        self,
        source_id: str,
        doc_id: str,
        title: str,
        chunk: str,
        parsed: Dict[str, Any],
        *,
        pii_flags: Optional[List[str]] = None,
        vocab: Optional[Vocabulary] = None,
    ) -> Tuple[int, int]:
        """Record a source chunk and merge its extracted graph (caller holds lock).

        Returns ``(entities_added, relationships_merged)``: entities that did not
        exist before, and relationships created or reinforced.
        """
        if vocab is None:
            vocab = self._vocabulary()
        source = {
            "id": source_id,
            "doc_id": doc_id,
            "title": title,
            "text": chunk,
            "created_at": time.time(),
        }
        if pii_flags:
            source["pii_flags"] = list(pii_flags)
        self.sources[source_id] = source
        self._mark("source", source_id)
        added_entities = 0
        added_relationships = 0
        local_ids: Dict[str, str] = {}
        unmapped_types: List[str] = []
        unmapped_predicates: List[str] = []
        for ent in parsed.get("entities", []) or []:
            if not isinstance(ent, dict):
                continue
            name = str(ent.get("name", "") or "")
            key = _norm(name)
            existed = key in self._name_index
            raw_type = str(ent.get("type", "concept") or "concept")
            etype, unmapped = vocab.resolve_type(raw_type) if vocab else (raw_type, None)
            eid = self._upsert_entity(
                name,
                etype,
                str(ent.get("description", "") or ""),
                source_id,
                pii_flags=pii_flags,
            )
            if eid:
                local_ids[key] = eid
                if not existed:
                    added_entities += 1
                    if unmapped:
                        self.entities[eid]["raw_type"] = unmapped
                if unmapped:
                    unmapped_types.append(unmapped)
                elif vocab is not None and not vocab.constrained:
                    # No certified vocabulary yet: every type is a candidate.
                    unmapped_types.append(etype)

        for rel in parsed.get("relationships", []) or []:
            if not isinstance(rel, dict):
                continue
            s_key = _norm(str(rel.get("source", "") or ""))
            t_key = _norm(str(rel.get("target", "") or ""))
            s_eid = local_ids.get(s_key) or self._name_index.get(s_key)
            t_eid = local_ids.get(t_key) or self._name_index.get(t_key)
            if s_eid and t_eid and s_eid != t_eid:
                predicate: Optional[str] = None
                raw_pred = str(rel.get("predicate", "") or "")
                if vocab is not None and raw_pred:
                    predicate, unmapped_p = vocab.resolve_predicate(raw_pred)
                    if unmapped_p:
                        unmapped_predicates.append(unmapped_p)
                elif vocab is not None and vocab.predicate_names:
                    # No predicate given: accept a description that is exactly a
                    # certified predicate or synonym (the same rule compile uses).
                    predicate = vocab.predicates.get(onto_key(str(rel.get("description", ""))))
                self._upsert_relationship(
                    s_eid,
                    t_eid,
                    str(rel.get("description", "") or ""),
                    source_id,
                    predicate=predicate,
                    pii_flags=pii_flags,
                )
                added_relationships += 1
        if self.ontology is not None and (unmapped_types or unmapped_predicates):
            known_t = vocab.known_types if vocab else set()
            known_p = vocab.known_predicates if vocab else set()
            self.ontology.record_proposals(
                [t for t in unmapped_types if t not in known_t],
                [p for p in unmapped_predicates if p.replace("_", " ") not in known_p],
            )
        return added_entities, added_relationships

    def ingest(
        self, title: str, text: str, model: str, *, actor: str = "system"
    ) -> Dict[str, Any]:
        """Chunk a document, extract a graph from each chunk, and merge it in.

        LLM extraction runs *before* taking the write lock, so a slow model
        never blocks readers or other writers; the merge is one transaction.
        """
        chunks = _chunk_text(text)
        if not chunks:
            raise ValueError("Document is empty.")
        prepared = [pii.prepare_chunk(chunk) for chunk in chunks]  # may raise PIIRejected

        doc_id = _new_id("doc")
        vocab = self._vocabulary()
        parsed_chunks = [self.extract_chunk(c, model, vocab=vocab) for c, _ in prepared]

        added_entities = 0
        added_relationships = 0
        flagged = sorted({f for _, flags in prepared for f in flags})
        with self._write():
            for idx, ((chunk, flags), parsed) in enumerate(zip(prepared, parsed_chunks)):
                ents, rels = self.merge_chunk(
                    f"{doc_id}#{idx}",
                    doc_id,
                    f"{title} [{idx + 1}/{len(chunks)}]",
                    chunk,
                    parsed,
                    pii_flags=flags,
                    vocab=vocab,
                )
                added_entities += ents
                added_relationships += rels
            self._audit(
                actor,
                "graph.ingest",
                doc_id,
                {
                    "title": title,
                    "chunks": len(chunks),
                    "entities_added": added_entities,
                    "relationships_added": added_relationships,
                    "pii_flags": flagged,
                },
            )
            entities_total = len(self.entities)
            relationships_total = len(self.relationships)

        return {
            "doc_id": doc_id,
            "title": title,
            "chunks_processed": len(chunks),
            "entities_total": entities_total,
            "relationships_total": relationships_total,
            "entities_added": added_entities,
            "relationships_added": added_relationships,
            "pii_flags": flagged,
        }

    # ------------------------------------------------------------------ #
    # Import (upload a pre-built knowledge graph)
    # ------------------------------------------------------------------ #
    def import_graph(
        self,
        graph: Dict[str, Any],
        *,
        fmt: str = "auto",
        source_type: str = "curated",
        merge_strategy: str = "preserve_curated",
        title: Optional[str] = None,
        origin_version: Optional[str] = None,
        actor: str = "system",
    ) -> Dict[str, Any]:
        """Import a pre-built knowledge graph produced by another tool.

        Supports Graphify (``graph.json``), Understand-Anything
        (``KnowledgeGraph``), AI Atlas taxonomy JSON, and arbitrary node/edge
        JSON. Imported nodes/edges are tagged with ``source_type`` provenance
        (default ``curated``) and their original id/version so reviewed content
        stays distinguishable from extracted or inferred additions.
        """
        if not isinstance(graph, dict):
            raise ValueError("Uploaded graph must be a JSON object.")
        if source_type not in _PROVENANCE_RANK:
            raise ValueError(
                f"source_type must be one of {sorted(_PROVENANCE_RANK)}."
            )
        if merge_strategy not in ("preserve_curated", "overwrite", "skip_existing"):
            raise ValueError(
                "merge_strategy must be preserve_curated, overwrite, or skip_existing."
            )
        fmt = (fmt or "auto").strip().lower()
        if fmt == "auto":
            fmt = _detect_format(graph)
        adapter = _FORMAT_ADAPTERS.get(fmt)
        if adapter is None:
            raise ValueError(f"Unsupported format '{fmt}'.")
        norm = adapter(graph)
        nodes = norm.get("nodes", [])
        edges = norm.get("edges", [])
        if not nodes:
            raise ValueError("No nodes found in the uploaded graph.")

        graph_format = norm.get("format", fmt)
        graph_title = (title or norm.get("title") or f"Imported {graph_format} graph").strip()
        version = origin_version or norm.get("version")
        overwrite = merge_strategy == "overwrite"

        # Apply the PII policy to node/edge descriptions before anything is stored.
        pii_by_node: Dict[int, List[str]] = {}
        for i, node in enumerate(nodes):
            desc, flags = pii.prepare_chunk(str(node.get("description", "") or ""))
            if flags:
                node["description"] = desc
                pii_by_node[i] = flags
        for edge in edges:
            desc, flags = pii.prepare_chunk(str(edge.get("description", "") or ""))
            if flags:
                edge["description"] = desc
                edge["_pii"] = flags

        snapshot_id: Optional[str] = None
        with self._write():
            if overwrite and self.store is not None and self.entities:
                snapshot_id = governance.create_snapshot(
                    self.store, f"before overwrite import of '{graph_title}'", actor
                )["id"]
            doc_id = _new_id("imp")
            source_id = f"{doc_id}#0"
            summary_text = norm.get("summary") or (
                f"Imported {graph_format} graph '{graph_title}' with "
                f"{len(nodes)} nodes and {len(edges)} edges."
            )
            self.sources[source_id] = {
                "id": source_id,
                "doc_id": doc_id,
                "title": graph_title,
                "text": summary_text,
                "created_at": time.time(),
                "source_type": source_type,
                "format": graph_format,
            }
            self._mark("source", source_id)

            origin_to_eid: Dict[str, str] = {}
            added_entities = 0
            updated_entities = 0
            skipped_entities = 0
            for i, node in enumerate(nodes):
                name = node.get("name")
                origin_id = node.get("origin_id")
                if not name:
                    continue
                key = _norm(name)
                exists = key in self._name_index
                if exists and merge_strategy == "skip_existing":
                    origin_to_eid[origin_id] = self._name_index[key]
                    skipped_entities += 1
                    continue
                origin = {"format": graph_format, "origin_id": origin_id}
                if version:
                    origin["origin_version"] = version
                if node.get("meta"):
                    origin["meta"] = node["meta"]
                eid = self._upsert_entity(
                    name,
                    node.get("type", "concept"),
                    node.get("description", ""),
                    source_id,
                    source_type=source_type,
                    origin=origin,
                    overwrite=overwrite,
                    pii_flags=pii_by_node.get(i),
                )
                if eid:
                    origin_to_eid[origin_id] = eid
                    if exists:
                        updated_entities += 1
                    else:
                        added_entities += 1

            added_relationships = 0
            skipped_relationships = 0
            for edge in edges:
                s_eid = origin_to_eid.get(edge.get("source"))
                t_eid = origin_to_eid.get(edge.get("target"))
                if not s_eid or not t_eid or s_eid == t_eid:
                    continue
                if merge_strategy == "skip_existing" and (
                    self._find_relationship(s_eid, t_eid) is not None
                ):
                    skipped_relationships += 1
                    continue
                self._upsert_relationship(
                    s_eid,
                    t_eid,
                    edge.get("description", ""),
                    source_id,
                    source_type=source_type,
                    origin={"format": graph_format},
                    overwrite=overwrite,
                    predicate=edge.get("predicate"),
                    pii_flags=edge.get("_pii"),
                )
                added_relationships += 1

            self._audit(
                actor,
                "graph.import",
                doc_id,
                {
                    "title": graph_title,
                    "format": graph_format,
                    "source_type": source_type,
                    "merge_strategy": merge_strategy,
                    "entities_added": added_entities,
                    "entities_updated": updated_entities,
                    "relationships_added": added_relationships,
                    "snapshot_id": snapshot_id,
                },
            )
            entities_total = len(self.entities)
            relationships_total = len(self.relationships)

        return {
            "doc_id": doc_id,
            "title": graph_title,
            "format": graph_format,
            "source_type": source_type,
            "merge_strategy": merge_strategy,
            "nodes_in_file": len(nodes),
            "edges_in_file": len(edges),
            "entities_added": added_entities,
            "entities_updated": updated_entities,
            "entities_skipped": skipped_entities,
            "relationships_added": added_relationships,
            "relationships_skipped": skipped_relationships,
            "entities_total": entities_total,
            "relationships_total": relationships_total,
            "snapshot_id": snapshot_id,
        }

    def export_graph(self) -> Dict[str, Any]:
        """Export the full graph (sources, entities, relationships) as JSON."""
        with self._read():
            return {
                "sources": {k: dict(v) for k, v in self.sources.items()},
                "entities": {k: dict(v) for k, v in self.entities.items()},
                "relationships": {k: dict(v) for k, v in self.relationships.items()},
                "stats": {
                    "entities": len(self.entities),
                    "relationships": len(self.relationships),
                    "sources": len(self.sources),
                },
            }

    # ------------------------------------------------------------------ #
    # Graph access / visualisation
    # ------------------------------------------------------------------ #
    def graph(self) -> Dict[str, Any]:
        with self._read():
            degree: Dict[str, int] = {eid: 0 for eid in self.entities}
            for rel in self.relationships.values():
                degree[rel["source"]] = degree.get(rel["source"], 0) + 1
                degree[rel["target"]] = degree.get(rel["target"], 0) + 1
            nodes = [
                {
                    "id": e["id"],
                    "name": e["name"],
                    "type": e["type"],
                    "description": e["description"],
                    "degree": degree.get(e["id"], 0),
                    "sources": e["sources"],
                    "source_type": e.get("source_type", _DEFAULT_SOURCE_TYPE),
                    "origin": e.get("origin"),
                    "pii_flags": e.get("pii_flags", []),
                }
                for e in self.entities.values()
            ]
            edges = [
                {
                    "id": r["id"],
                    "source": r["source"],
                    "target": r["target"],
                    "description": r["description"],
                    "predicate": r.get("predicate"),
                    "sources": r["sources"],
                    "source_type": r.get("source_type", _DEFAULT_SOURCE_TYPE),
                    "origin": r.get("origin"),
                    "pii_flags": r.get("pii_flags", []),
                }
                for r in self.relationships.values()
            ]
            sources_total = len(self.sources)
            version = self._version
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "entities": len(nodes),
                "relationships": len(edges),
                "sources": sources_total,
                "graph_version": version,
            },
        }

    def clear(self, *, actor: str = "system") -> Dict[str, Any]:
        """Wipe the graph. A snapshot is taken first, so this can be undone."""
        with self._lock:
            if self.store is None:
                self.sources.clear()
                self.entities.clear()
                self.relationships.clear()
                self._name_index.clear()
                self._rel_index.clear()
                self._save()
                return {"snapshot_id": None}
            with self.store.transaction():
                self._sync()
                snapshot_id = None
                if self.entities or self.sources:
                    snapshot_id = governance.create_snapshot(
                        self.store, "before clear", actor
                    )["id"]
                self.store.replace_graph({}, {}, {})
                self._audit(actor, "graph.clear", "", {"snapshot_id": snapshot_id})
            self._reload_all()
            return {"snapshot_id": snapshot_id}

    # ------------------------------------------------------------------ #
    # Snapshots, entity details, curation
    # ------------------------------------------------------------------ #
    def snapshot(self, label: str = "", *, actor: str = "system") -> Dict[str, Any]:
        if self.store is None:
            raise RuntimeError("Snapshots need the shared store.")
        with self._lock, self.store.transaction():
            snap = governance.create_snapshot(self.store, label, actor)
            self._audit(actor, "graph.snapshot", snap["id"], {"label": label})
        return snap

    def restore(self, snapshot_id: str, *, actor: str = "system") -> Dict[str, Any]:
        """Replace the graph with a snapshot (the current graph is snapshotted first)."""
        if self.store is None:
            raise RuntimeError("Snapshots need the shared store.")
        with self._lock:
            with self.store.transaction():
                data = governance.load_snapshot(self.store, snapshot_id)
                backup = governance.create_snapshot(
                    self.store, f"before restore of {snapshot_id}", actor
                )
                self.store.replace_graph(
                    data["sources"], data["entities"], data["relationships"]
                )
                governance.restore_term_links(self.store, data.get("term_entity", []))
                self._audit(
                    actor, "graph.restore", snapshot_id, {"backup_snapshot_id": backup["id"]}
                )
            self._reload_all()
            return {
                "restored": snapshot_id,
                "backup_snapshot_id": backup["id"],
                "entities": len(self.entities),
                "relationships": len(self.relationships),
                "sources": len(self.sources),
            }

    def entity(self, entity_id_or_name: str) -> Optional[Dict[str, Any]]:
        """One entity with its neighbours, backing sources and glossary terms."""
        with self._read():
            eid = entity_id_or_name
            if eid not in self.entities:
                eid = self._name_index.get(_norm(entity_id_or_name), "")
            ent = self.entities.get(eid)
            if ent is None:
                return None
            neighbors = []
            for rel in self.relationships.values():
                if rel["source"] == eid or rel["target"] == eid:
                    other = rel["target"] if rel["source"] == eid else rel["source"]
                    other_ent = self.entities.get(other, {})
                    neighbors.append(
                        {
                            "relationship_id": rel["id"],
                            "direction": "out" if rel["source"] == eid else "in",
                            "entity_id": other,
                            "name": other_ent.get("name", "?"),
                            "type": other_ent.get("type", ""),
                            "predicate": rel.get("predicate"),
                            "description": rel.get("description", ""),
                        }
                    )
            sources = [self.sources[s] for s in ent.get("sources", []) if s in self.sources]
            out = {**ent, "neighbors": neighbors, "source_records": sources}
        out["terms"] = self.ontology.terms_for_entity(eid) if self.ontology else []
        return out

    def merge_entities(self, keep_id: str, drop_id: str, *, actor: str = "system") -> Dict[str, Any]:
        """Fold ``drop_id`` into ``keep_id``: sources, relationships and term links."""
        if keep_id == drop_id:
            raise ValueError("Cannot merge an entity into itself.")
        with self._write():
            keep = self.entities.get(keep_id)
            drop = self.entities.get(drop_id)
            if keep is None or drop is None:
                raise KeyError(keep_id if keep is None else drop_id)
            for sid in drop.get("sources", []):
                if sid not in keep["sources"]:
                    keep["sources"].append(sid)
            if drop.get("pii_flags"):
                keep["pii_flags"] = sorted(set(keep.get("pii_flags", [])) | set(drop["pii_flags"]))
            aliases = keep.setdefault("aliases", [])
            if drop["name"] not in aliases:
                aliases.append(drop["name"])
            if not keep.get("description") and drop.get("description"):
                keep["description"] = drop["description"]
            self._mark("entity", keep_id)
            rewired = 0
            for rid, rel in list(self.relationships.items()):
                if drop_id not in (rel["source"], rel["target"]):
                    continue
                s = keep_id if rel["source"] == drop_id else rel["source"]
                t = keep_id if rel["target"] == drop_id else rel["target"]
                del self.relationships[rid]
                self._mark_deleted("relationship", rid)
                if s == t:
                    continue
                self._rel_index = {}
                for sid in rel.get("sources", []):
                    self._upsert_relationship(
                        s,
                        t,
                        rel.get("description", ""),
                        sid,
                        source_type=rel.get("source_type", _DEFAULT_SOURCE_TYPE),
                        origin=rel.get("origin"),
                        predicate=rel.get("predicate"),
                        pii_flags=rel.get("pii_flags"),
                    )
                rewired += 1
            del self.entities[drop_id]
            self._name_index.pop(_norm(drop["name"]), None)
            self._rel_index = {}
            self._mark_deleted("entity", drop_id)
            if self.store is not None:
                conn = self.store.conn
                conn.execute(
                    "INSERT OR IGNORE INTO term_entity(term_id, entity_id) "
                    "SELECT term_id, ? FROM term_entity WHERE entity_id = ?",
                    (keep_id, drop_id),
                )
                conn.execute("DELETE FROM term_entity WHERE entity_id = ?", (drop_id,))
            self._audit(
                actor,
                "graph.merge_entities",
                keep_id,
                {"dropped": drop_id, "dropped_name": drop["name"], "rewired": rewired},
            )
        return {"kept": keep_id, "dropped": drop_id, "relationships_rewired": rewired}

    def update_rows(
        self,
        *,
        entity_types: Optional[Dict[str, str]] = None,
        predicates: Optional[Dict[str, Optional[str]]] = None,
        actor: str = "system",
        action: str = "graph.update",
    ) -> Dict[str, int]:
        """Bulk-set entity types / relationship predicates (used by compile)."""
        changed = {"entities": 0, "relationships": 0}
        with self._write():
            for eid, etype in (entity_types or {}).items():
                ent = self.entities.get(eid)
                if ent is not None and ent.get("type") != etype:
                    ent.setdefault("raw_type", ent.get("type"))
                    ent["type"] = etype
                    self._mark("entity", eid)
                    changed["entities"] += 1
            for rid, pred in (predicates or {}).items():
                rel = self.relationships.get(rid)
                if rel is not None and rel.get("predicate") != pred:
                    rel["predicate"] = pred
                    self._mark("relationship", rid)
                    changed["relationships"] += 1
            if any(changed.values()):
                self._audit(actor, action, "", changed)
        return changed

    # ------------------------------------------------------------------ #
    # Retrieval + reasoning
    # ------------------------------------------------------------------ #
    def _seed_entities(self, query: str) -> List[str]:
        """Match the question to entities. Returns [] when nothing matches.

        An entity is a seed when its full name appears in the question as a
        phrase, when a content word of the question starts a word of its name,
        or when it is linked to a glossary term the question mentions.
        """
        q = _norm(query)
        tokens = _query_tokens(q)
        token_res = [re.compile(rf"(?<!\w){re.escape(t)}") for t in tokens]
        seeds: List[str] = []
        for eid, ent in self.entities.items():
            name = _norm(ent["name"])
            if not name:
                continue
            phrase_hit = re.search(rf"(?<!\w){re.escape(name)}(?!\w)", q) is not None
            if phrase_hit or any(rx.search(name) for rx in token_res):
                seeds.append(eid)
        for eid in self._term_seeds(query):
            if eid not in seeds:
                seeds.append(eid)
        return seeds

    def _term_seeds(self, query: str) -> List[str]:
        if self.ontology is None:
            return []
        out: List[str] = []
        for term in self.ontology.match_terms(query):
            for eid in term["entity_ids"]:
                if eid in self.entities and eid not in out:
                    out.append(eid)
        return out

    def _expand(
        self, seeds: List[str], max_depth: int, max_nodes: int
    ) -> Tuple[List[str], List[str]]:
        """Breadth-first multi-hop expansion from the seed entities."""
        adjacency: Dict[str, List[Tuple[str, str]]] = {eid: [] for eid in self.entities}
        for rid, rel in self.relationships.items():
            adjacency.setdefault(rel["source"], []).append((rel["target"], rid))
            adjacency.setdefault(rel["target"], []).append((rel["source"], rid))

        visited = set()
        used_edges: set = set()
        queue: deque = deque((s, 0) for s in seeds)
        order: List[str] = []
        while queue and len(visited) < max_nodes:
            eid, depth = queue.popleft()
            if eid in visited or eid not in self.entities:
                continue
            visited.add(eid)
            order.append(eid)
            if depth >= max_depth:
                continue
            for neighbor, rid in adjacency.get(eid, []):
                used_edges.add(rid)
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        return order, list(used_edges)

    def retrieve(
        self, query: str, max_depth: int = 2, max_nodes: int = 25
    ) -> Dict[str, Any]:
        with self._read():
            seeds = self._seed_entities(query)
            node_ids, edge_ids = self._expand(seeds, max_depth, max_nodes)
            nodes = [self.entities[n] for n in node_ids if n in self.entities]
            edges = [self.relationships[e] for e in edge_ids if e in self.relationships]
            # Gather the source chunks backing this subgraph.
            source_ids: List[str] = []
            for item in nodes + edges:
                for sid in item.get("sources", []):
                    if sid not in source_ids:
                        source_ids.append(sid)
            sources = [self.sources[s] for s in source_ids if s in self.sources]
        return {
            "seeds": seeds,
            "nodes": nodes,
            "edges": edges,
            "sources": sources,
        }

    def _abstain(
        self,
        answer: str,
        *,
        reason: str,
        question: str,
        model: str,
        mode: str,
        actor: str,
        answerability: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "answer": answer,
            "abstained": True,
            "abstain_reason": reason,
            "mode": mode,
            "citations": [],
            "grounded": False,
            "unknown_citations": [],
            "retrieved_source_ids": [],
            "reasoning_path": [],
            "subgraph": {"nodes": [], "edges": []},
        }
        if answerability is not None:
            result["answerability"] = answerability
        result["answer_id"] = self._receipt(question, model, mode, actor, result, seeds=[])
        return result

    def _receipt(
        self,
        question: str,
        model: str,
        mode: str,
        actor: str,
        result: Dict[str, Any],
        *,
        seeds: List[str],
    ) -> Optional[str]:
        """Persist an answer receipt (store-backed engines only)."""
        if self.store is None:
            return None
        evidence = {
            "seeds": seeds,
            "node_ids": [n["id"] for n in result["subgraph"]["nodes"]],
            "edges": [[e["source"], e["target"]] for e in result["subgraph"]["edges"]],
            "retrieved_source_ids": result["retrieved_source_ids"],
            "cited_source_ids": [c["id"] for c in result["citations"]],
            "unknown_citations": result["unknown_citations"],
            "abstain_reason": result.get("abstain_reason"),
        }
        if "answerability" in result:
            evidence["matched_terms"] = result["answerability"].get("matched_terms", [])
            evidence["coverage"] = result["answerability"].get("coverage")
        return governance.record_answer(
            self.store,
            question=question,
            answer=result["answer"],
            mode=mode,
            model=model,
            grounded=bool(result["grounded"]),
            abstained=bool(result["abstained"]),
            evidence=evidence,
            actor=actor,
        )

    def query(
        self,
        question: str,
        model: str,
        max_depth: int = 2,
        max_nodes: int = 25,
        *,
        mode: str = "exploratory",
        actor: str = "",
    ) -> Dict[str, Any]:
        """Answer a question grounded in the knowledge graph, with citations.

        ``mode="exploratory"`` (default) answers whenever an entity matches.
        ``mode="governed"`` first runs :func:`veritasgraph.answerability.check_answerable`
        and abstains unless certified glossary terms cover the question; an
        ungrounded answer is withheld rather than returned with a warning.
        Every answer (and abstention) is recorded as a receipt with an
        ``answer_id`` when the engine is store-backed.
        """
        if mode not in ("exploratory", "governed"):
            raise ValueError("mode must be 'exploratory' or 'governed'.")
        with self._read():
            empty = not self.entities
        if empty:
            return self._abstain(
                "The knowledge graph is empty. Ingest a document first.",
                reason="empty_graph",
                question=question,
                model=model,
                mode=mode,
                actor=actor,
            )

        answerability: Optional[Dict[str, Any]] = None
        if mode == "governed":
            from veritasgraph.answerability import check_answerable

            answerability = check_answerable(self, question, mode="governed")
            if not answerability["answerable"]:
                return self._abstain(
                    "I can't give a governed answer to this: " + answerability["reason"],
                    reason="not_answerable",
                    question=question,
                    model=model,
                    mode=mode,
                    actor=actor,
                    answerability=answerability,
                )

        ctx = self.retrieve(question, max_depth=max_depth, max_nodes=max_nodes)
        if not ctx["seeds"]:
            return self._abstain(
                "I can't answer this from the knowledge graph: none of the entities "
                "in the question appear in it.",
                reason="no_matching_entities",
                question=question,
                model=model,
                mode=mode,
                actor=actor,
                answerability=answerability,
            )
        id_to_name = {e["id"]: e["name"] for e in ctx["nodes"]}

        # Build a reasoning path from the relationships (multi-hop chain).
        reasoning_path = [
            f"{id_to_name.get(r['source'], '?')} --[{r.get('predicate') or r['description'] or 'related to'}]--> "
            f"{id_to_name.get(r['target'], '?')}"
            for r in ctx["edges"]
        ]

        entity_lines = [
            f"- {e['name']} ({e['type']}): {e['description']}" for e in ctx["nodes"]
        ]
        rel_lines = reasoning_path
        source_lines = [f"[{s['id']}] {s['title']}: {s['text']}" for s in ctx["sources"]]

        context = (
            "ENTITIES:\n" + "\n".join(entity_lines) + "\n\n"
            "RELATIONSHIPS:\n" + "\n".join(rel_lines) + "\n\n"
            "SOURCES:\n" + "\n\n".join(source_lines)
        )
        system = (
            "You are VeritasGraph, a graph-grounded reasoning assistant. Answer the "
            "question using ONLY the provided knowledge-graph context and sources. "
            "Reason across multiple relationships when needed (multi-hop). Every "
            "factual claim must cite the source id(s) it came from in square brackets, "
            "e.g. [doc_xxx#0]. If the context is insufficient, say so explicitly."
        )
        user = f"CONTEXT:\n{context}\n\nQUESTION: {question}"

        answer = self._chat(
            model,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        # Only sources that were actually retrieved count as citations; ids the
        # model invented are reported, and nothing is cited on its behalf.
        cited_ids = set(_SOURCE_ID_RE.findall(answer or ""))
        retrieved = {s["id"]: s for s in ctx["sources"]}
        citations = [
            {"id": sid, "title": s["title"], "text": s["text"]}
            for sid, s in retrieved.items()
            if sid in cited_ids
        ]
        unknown_citations = sorted(cited_ids - retrieved.keys())
        grounded = bool(citations) and not unknown_citations

        result: Dict[str, Any] = {
            "answer": answer,
            "abstained": False,
            "mode": mode,
            "citations": citations,
            "grounded": grounded,
            "unknown_citations": unknown_citations,
            "retrieved_source_ids": list(retrieved.keys()),
            "reasoning_path": reasoning_path,
            "subgraph": {
                "nodes": [
                    {"id": e["id"], "name": e["name"], "type": e["type"]}
                    for e in ctx["nodes"]
                ],
                "edges": [
                    {
                        "source": r["source"],
                        "target": r["target"],
                        "description": r["description"],
                        "predicate": r.get("predicate"),
                    }
                    for r in ctx["edges"]
                ],
            },
        }
        if answerability is not None:
            result["answerability"] = answerability
        if mode == "governed" and not grounded:
            # Governed mode never hands out an answer it cannot trace to sources;
            # the ungrounded text is discarded, not returned alongside.
            result["answer"] = (
                "The model's answer was withheld: it did not cite the retrieved "
                "sources" + (" (it cited unknown ids)" if unknown_citations else "") + "."
            )
            result["abstained"] = True
            result["abstain_reason"] = "ungrounded_answer"
        result["answer_id"] = self._receipt(
            question, model, mode, actor, result, seeds=ctx["seeds"]
        )
        return result


# Process-wide singleton, mirroring studio_api.store.store.
engine = GraphRAGEngine()
