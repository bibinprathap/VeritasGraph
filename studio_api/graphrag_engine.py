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
        self, name: str, etype: str, description: str, source_id: str
    ) -> Optional[str]:
        key = _norm(name)
        if not key:
            return None
        eid = self._name_index.get(key)
        if eid is None:
            eid = _new_id("ent")
            self.entities[eid] = {
                "id": eid,
                "name": name.strip(),
                "type": (etype or "concept").strip().lower(),
                "description": (description or "").strip(),
                "sources": [source_id],
            }
            self._name_index[key] = eid
        else:
            entity = self.entities[eid]
            if source_id not in entity["sources"]:
                entity["sources"].append(source_id)
            if description and len(description) > len(entity.get("description", "")):
                entity["description"] = description.strip()
        return eid

    def _upsert_relationship(
        self, source_eid: str, target_eid: str, description: str, source_id: str
    ) -> None:
        for rel in self.relationships.values():
            if rel["source"] == source_eid and rel["target"] == target_eid:
                if source_id not in rel["sources"]:
                    rel["sources"].append(source_id)
                if description and len(description) > len(rel.get("description", "")):
                    rel["description"] = description.strip()
                return
        rid = _new_id("rel")
        self.relationships[rid] = {
            "id": rid,
            "source": source_eid,
            "target": target_eid,
            "description": (description or "").strip(),
            "sources": [source_id],
        }

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
