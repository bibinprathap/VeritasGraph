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

The graph is held in memory and snapshotted to JSON so it survives a restart,
matching the persistence approach of :class:`studio_api.store.StudioStore`.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

_DATA_DIR = Path(
    os.getenv("STUDIO_DATA_DIR", str(Path(__file__).resolve().parent / "data"))
)
_GRAPH_SNAPSHOT = _DATA_DIR / "knowledge_graph.json"

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
    return re.sub(r"\s+", " ", name or "").strip().lower()


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
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        if not _GRAPH_SNAPSHOT.is_file():
            return
        try:
            data = json.loads(_GRAPH_SNAPSHOT.read_text())
        except (json.JSONDecodeError, OSError):
            return
        self.sources = data.get("sources", {})
        self.entities = data.get("entities", {})
        self.relationships = data.get("relationships", {})
        self._name_index = {
            _norm(e["name"]): eid for eid, e in self.entities.items()
        }

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "sources": self.sources,
            "entities": self.entities,
            "relationships": self.relationships,
        }
        tmp = _GRAPH_SNAPSHOT.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot, indent=2))
        tmp.replace(_GRAPH_SNAPSHOT)

    # ------------------------------------------------------------------ #
    # LLM access
    # ------------------------------------------------------------------ #
    def _chat(self, model: str, messages: List[Dict[str, str]]) -> str:
        url = f"{_ollama_base()}/api/chat"
        body = {"model": model, "messages": messages, "stream": False}
        with httpx.Client(timeout=180.0) as client:
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
            self.entities[eid] = entity
            self._name_index[key] = eid
        else:
            entity = self.entities[eid]
            if source_id not in entity["sources"]:
                entity["sources"].append(source_id)
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
        return eid

    def _find_relationship(self, source_eid: str, target_eid: str) -> Optional[str]:
        for rid, rel in self.relationships.items():
            if rel["source"] == source_eid and rel["target"] == target_eid:
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
    ) -> None:
        rid = self._find_relationship(source_eid, target_eid)
        if rid is not None:
            rel = self.relationships[rid]
            if source_id not in rel["sources"]:
                rel["sources"].append(source_id)
            new_rank = _provenance_rank(source_type)
            old_rank = _provenance_rank(rel.get("source_type"))
            incoming_desc = (description or "").strip()
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
        if origin:
            rel["origin"] = origin
        self.relationships[rid] = rel

    def ingest(self, title: str, text: str, model: str) -> Dict[str, Any]:
        """Chunk a document, extract a graph from each chunk, and merge it in."""
        chunks = _chunk_text(text)
        if not chunks:
            raise ValueError("Document is empty.")

        doc_id = _new_id("doc")
        added_entities = 0
        added_relationships = 0
        chunks_processed = 0

        with self._lock:
            for idx, chunk in enumerate(chunks):
                source_id = f"{doc_id}#{idx}"
                self.sources[source_id] = {
                    "id": source_id,
                    "doc_id": doc_id,
                    "title": f"{title} [{idx + 1}/{len(chunks)}]",
                    "text": chunk,
                    "created_at": time.time(),
                }
                raw = self._chat(
                    model,
                    [
                        {"role": "system", "content": _EXTRACTION_SYSTEM},
                        {"role": "user", "content": chunk},
                    ],
                )
                parsed = _extract_json(raw)
                chunks_processed += 1

                local_ids: Dict[str, str] = {}
                for ent in parsed.get("entities", []) or []:
                    if not isinstance(ent, dict):
                        continue
                    name = ent.get("name", "")
                    eid = self._upsert_entity(
                        name,
                        ent.get("type", "concept"),
                        ent.get("description", ""),
                        source_id,
                    )
                    if eid:
                        before = eid in self.entities
                        local_ids[_norm(name)] = eid
                        added_entities += 1 if before else 0

                for rel in parsed.get("relationships", []) or []:
                    if not isinstance(rel, dict):
                        continue
                    s_key = _norm(rel.get("source", ""))
                    t_key = _norm(rel.get("target", ""))
                    s_eid = local_ids.get(s_key) or self._name_index.get(s_key)
                    t_eid = local_ids.get(t_key) or self._name_index.get(t_key)
                    if s_eid and t_eid and s_eid != t_eid:
                        self._upsert_relationship(
                            s_eid, t_eid, rel.get("description", ""), source_id
                        )
                        added_relationships += 1
            self._save()

        return {
            "doc_id": doc_id,
            "title": title,
            "chunks_processed": chunks_processed,
            "entities_total": len(self.entities),
            "relationships_total": len(self.relationships),
            "relationships_added": added_relationships,
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

        with self._lock:
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

            origin_to_eid: Dict[str, str] = {}
            added_entities = 0
            updated_entities = 0
            skipped_entities = 0
            for node in nodes:
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
                )
                added_relationships += 1

            self._save()

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
            "entities_total": len(self.entities),
            "relationships_total": len(self.relationships),
        }

    def export_graph(self) -> Dict[str, Any]:
        """Export the full graph (sources, entities, relationships) as JSON."""
        with self._lock:
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
        with self._lock:
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
                }
                for e in self.entities.values()
            ]
            edges = [
                {
                    "id": r["id"],
                    "source": r["source"],
                    "target": r["target"],
                    "description": r["description"],
                    "sources": r["sources"],
                    "source_type": r.get("source_type", _DEFAULT_SOURCE_TYPE),
                    "origin": r.get("origin"),
                }
                for r in self.relationships.values()
            ]
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "entities": len(nodes),
                "relationships": len(edges),
                "sources": len(self.sources),
            },
        }

    def clear(self) -> None:
        with self._lock:
            self.sources.clear()
            self.entities.clear()
            self.relationships.clear()
            self._name_index.clear()
            self._save()

    # ------------------------------------------------------------------ #
    # Retrieval + reasoning
    # ------------------------------------------------------------------ #
    def _seed_entities(self, query: str) -> List[str]:
        """Match query terms to entity names (case-insensitive substring)."""
        q = query.lower()
        seeds: List[str] = []
        for eid, ent in self.entities.items():
            name = ent["name"].lower()
            if name and (name in q or any(tok in name for tok in q.split() if len(tok) > 3)):
                seeds.append(eid)
        # Fall back to the highest-degree nodes when nothing matches.
        if not seeds:
            degree: Dict[str, int] = {eid: 0 for eid in self.entities}
            for rel in self.relationships.values():
                degree[rel["source"]] = degree.get(rel["source"], 0) + 1
                degree[rel["target"]] = degree.get(rel["target"], 0) + 1
            seeds = sorted(degree, key=degree.get, reverse=True)[:3]
        return seeds

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
        with self._lock:
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

    def query(
        self, question: str, model: str, max_depth: int = 2, max_nodes: int = 25
    ) -> Dict[str, Any]:
        """Answer a question grounded in the knowledge graph, with citations."""
        if not self.entities:
            return {
                "answer": "The knowledge graph is empty. Ingest a document first.",
                "citations": [],
                "reasoning_path": [],
                "subgraph": {"nodes": [], "edges": []},
            }

        ctx = self.retrieve(question, max_depth=max_depth, max_nodes=max_nodes)
        id_to_name = {e["id"]: e["name"] for e in ctx["nodes"]}

        # Build a reasoning path from the relationships (multi-hop chain).
        reasoning_path = [
            f"{id_to_name.get(r['source'], '?')} --[{r['description'] or 'related to'}]--> "
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

        cited_ids = set(re.findall(r"\[([a-z0-9]+#\d+)\]", answer))
        citations = [
            {"id": s["id"], "title": s["title"], "text": s["text"]}
            for s in ctx["sources"]
            if s["id"] in cited_ids
        ]
        # If the model didn't cite explicitly, surface the retrieved sources.
        if not citations:
            citations = [
                {"id": s["id"], "title": s["title"], "text": s["text"]}
                for s in ctx["sources"]
            ]

        return {
            "answer": answer,
            "citations": citations,
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
                    }
                    for r in ctx["edges"]
                ],
            },
        }


# Process-wide singleton, mirroring studio_api.store.store.
engine = GraphRAGEngine()
