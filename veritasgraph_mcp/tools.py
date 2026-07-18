"""VeritasGraph MCP tools — thin wrappers over the local GraphRAG engine.

Each tool handler takes a plain ``dict`` of arguments and returns a plain
JSON-serialisable ``dict``. Errors are returned as ``{"error": "..."}`` rather
than raised, so the server can report ``isError`` to the MCP client without
crashing the stdio loop.

The engine is imported lazily so that ``tools/list`` (schema discovery) never
requires the heavier VeritasGraph runtime to be importable — an IDE can inspect
the available tools before Ollama or the graph store are ready.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List

log = logging.getLogger("veritasgraph.mcp.tools")


def _default_model() -> str:
    return os.getenv("VERITASGRAPH_MODEL", "qwen3:latest").strip() or "qwen3:latest"


def _engine():
    """Lazily import and return the shared GraphRAG engine singleton."""
    from studio_api.graphrag_engine import engine

    return engine


# --------------------------------------------------------------------------- #
# Handlers
# --------------------------------------------------------------------------- #
def handle_ingest_document(args: dict) -> dict:
    """Build/extend the knowledge graph from a document."""
    text = str(args.get("text", "")).strip()
    if not text:
        return {"error": "text is required"}
    title = str(args.get("title", "") or "Untitled document").strip()
    model = str(args.get("model", "") or _default_model()).strip()
    try:
        result = _engine().ingest(title, text, model)
        return {"status": "ingested", **result}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - surface a clean MCP error
        log.exception("ingest_document failed")
        return {"error": str(exc)}


def handle_query_graph(args: dict) -> dict:
    """Answer a question grounded in the knowledge graph, with citations."""
    question = str(args.get("question", "")).strip()
    if not question:
        return {"error": "question is required"}
    model = str(args.get("model", "") or _default_model()).strip()
    try:
        max_depth = int(args.get("max_depth", 2))
        max_nodes = int(args.get("max_nodes", 25))
    except (TypeError, ValueError):
        return {"error": "max_depth and max_nodes must be integers"}
    try:
        return _engine().query(question, model, max_depth, max_nodes)
    except Exception as exc:  # noqa: BLE001
        log.exception("query_graph failed")
        return {"error": str(exc)}


def handle_search_entities(args: dict) -> dict:
    """Retrieve the subgraph most relevant to a query (no LLM call)."""
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query is required", "nodes": [], "edges": []}
    try:
        max_depth = int(args.get("max_depth", 2))
        max_nodes = int(args.get("max_nodes", 25))
    except (TypeError, ValueError):
        return {"error": "max_depth and max_nodes must be integers"}
    try:
        ctx = _engine().retrieve(query, max_depth=max_depth, max_nodes=max_nodes)
        return {
            "seeds": ctx.get("seeds", []),
            "nodes": [
                {"id": n["id"], "name": n["name"], "type": n["type"],
                 "description": n["description"], "sources": n.get("sources", [])}
                for n in ctx.get("nodes", [])
            ],
            "edges": [
                {"id": e["id"], "source": e["source"], "target": e["target"],
                 "description": e["description"], "sources": e.get("sources", [])}
                for e in ctx.get("edges", [])
            ],
            "source_count": len(ctx.get("sources", [])),
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("search_entities failed")
        return {"error": str(exc), "nodes": [], "edges": []}


def handle_get_graph(_args: dict) -> dict:
    """Return the full knowledge graph (nodes, edges, and stats)."""
    try:
        return _engine().graph()
    except Exception as exc:  # noqa: BLE001
        log.exception("get_graph failed")
        return {"error": str(exc)}


def handle_import_graph(args: dict) -> dict:
    """Import a pre-built knowledge graph (Graphify / Understand-Anything / AI Atlas / generic)."""
    graph = args.get("graph")
    if not isinstance(graph, dict):
        return {"error": "graph must be a JSON object with nodes and edges"}
    try:
        result = _engine().import_graph(
            graph,
            fmt=str(args.get("format", "auto") or "auto"),
            source_type=str(args.get("source_type", "curated") or "curated"),
            merge_strategy=str(args.get("merge_strategy", "preserve_curated") or "preserve_curated"),
            title=args.get("title"),
            origin_version=args.get("origin_version"),
        )
        return {"status": "imported", **result}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        log.exception("import_graph failed")
        return {"error": str(exc)}


def handle_clear_graph(_args: dict) -> dict:
    """Delete every node, edge, and source from the knowledge graph."""
    try:
        _engine().clear()
        return {"status": "cleared"}
    except Exception as exc:  # noqa: BLE001
        log.exception("clear_graph failed")
        return {"error": str(exc)}


# --------------------------------------------------------------------------- #
# Tool definitions (exposed via tools/list)
# --------------------------------------------------------------------------- #
_MODEL_PROP = {
    "type": "string",
    "description": "Local Ollama model to use (defaults to $VERITASGRAPH_MODEL).",
}

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "veritasgraph_ingest_document",
        "description": (
            "Ingest a document into the VeritasGraph knowledge graph. Chunks the "
            "text, extracts entities and relationships with a local model, and "
            "records the source chunk behind every node/edge for verifiable "
            "attribution."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Full document text to ingest."},
                "title": {"type": "string", "description": "Human-readable document title."},
                "model": _MODEL_PROP,
            },
            "required": ["text"],
        },
        "_handler": handle_ingest_document,
    },
    {
        "name": "veritasgraph_query",
        "description": (
            "Ask a question and get a graph-grounded, multi-hop answer with "
            "verifiable [doc#chunk] citations and the reasoning path used."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Natural-language question."},
                "model": _MODEL_PROP,
                "max_depth": {"type": "integer", "description": "Max graph hops (default 2)."},
                "max_nodes": {"type": "integer", "description": "Max subgraph nodes (default 25)."},
            },
            "required": ["question"],
        },
        "_handler": handle_query_graph,
    },
    {
        "name": "veritasgraph_search_entities",
        "description": (
            "Retrieve the subgraph most relevant to a query (entities, "
            "relationships, seeds) without invoking the LLM. Fast graph lookup."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query / topic."},
                "max_depth": {"type": "integer", "description": "Max graph hops (default 2)."},
                "max_nodes": {"type": "integer", "description": "Max subgraph nodes (default 25)."},
            },
            "required": ["query"],
        },
        "_handler": handle_search_entities,
    },
    {
        "name": "veritasgraph_get_graph",
        "description": "Return the full knowledge graph: all nodes, edges, and stats.",
        "inputSchema": {"type": "object", "properties": {}},
        "_handler": handle_get_graph,
    },
    {
        "name": "veritasgraph_import_graph",
        "description": (
            "Import a pre-built knowledge graph produced by another tool "
            "(Graphify graph.json, Understand-Anything KnowledgeGraph, AI Atlas "
            "taxonomy JSON, or any node/edge JSON). Imported nodes/edges are "
            "tagged with source_type provenance (curated/extracted/inferred) and "
            "their original id/version so curated content stays distinguishable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "graph": {"type": "object", "description": "Raw uploaded graph JSON (nodes + edges)."},
                "format": {"type": "string", "description": "auto | graphify | understand_anything | ai_atlas | generic."},
                "source_type": {"type": "string", "description": "Provenance: curated | extracted | inferred (default curated)."},
                "merge_strategy": {"type": "string", "description": "preserve_curated | overwrite | skip_existing."},
                "title": {"type": "string", "description": "Optional display title for the imported graph."},
                "origin_version": {"type": "string", "description": "Optional source version/commit to preserve."},
            },
            "required": ["graph"],
        },
        "_handler": handle_import_graph,
    },
    {
        "name": "veritasgraph_clear_graph",
        "description": "Clear the entire knowledge graph (destructive; removes all data).",
        "inputSchema": {"type": "object", "properties": {}},
        "_handler": handle_clear_graph,
    },
]


# --------------------------------------------------------------------------- #
# Resources (exposed via resources/list + resources/read)
# --------------------------------------------------------------------------- #
RESOURCE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "uri": "veritasgraph://graph",
        "name": "VeritasGraph knowledge graph",
        "description": "Live snapshot of the local knowledge graph (nodes, edges, stats).",
        "mimeType": "application/json",
    },
    {
        "uri": "veritasgraph://stats",
        "name": "VeritasGraph statistics",
        "description": "Counts of entities, relationships, and source chunks.",
        "mimeType": "application/json",
    },
]


def handle_resource_read(uri: str) -> Dict[str, Any]:
    """Resolve a ``veritasgraph://`` resource URI to its JSON text payload."""
    import json

    uri = (uri or "").strip()
    if uri == "veritasgraph://graph":
        payload: Any = _engine().graph()
    elif uri == "veritasgraph://stats":
        payload = _engine().graph().get("stats", {})
    else:
        payload = {"error": f"Unknown resource: {uri}"}
    return {
        "uri": uri,
        "mimeType": "application/json",
        "text": json.dumps(payload, ensure_ascii=False),
    }


TOOL_HANDLERS: Dict[str, Callable[[dict], dict]] = {
    t["name"]: t["_handler"] for t in TOOL_DEFINITIONS
}
