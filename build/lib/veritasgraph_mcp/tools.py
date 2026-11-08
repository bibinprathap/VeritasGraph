"""VeritasGraph MCP tools — thin wrappers over the local GraphRAG engine.

Each tool handler takes a plain ``dict`` of arguments and returns a plain
JSON-serialisable ``dict``. Errors are returned as ``{"error": "..."}`` rather
than raised, so the server can report ``isError`` to the MCP client without
crashing the stdio loop.

Every tool declares the mode it needs (``read`` < ``write`` < ``admin``). The
server exposes only tools at or below the effective mode, which is
``VERITASGRAPH_MCP_MODE`` (default ``write``) capped by the caller's role when
the tools are reached through the Studio HTTP bridge. Text from PII-flagged
sources is redacted for ``read`` callers.

The engine is imported lazily so that ``tools/list`` (schema discovery) never
requires the heavier VeritasGraph runtime to be importable — an IDE can inspect
the available tools before Ollama or the graph store are ready.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from contextvars import ContextVar
from typing import Any, Callable, Dict, Iterator, List, Optional

from veritasgraph import pii

log = logging.getLogger("veritasgraph.mcp.tools")

MODES = ("read", "write", "admin")
_MODE_RANK = {m: i for i, m in enumerate(MODES)}
ROLE_MODE = {"viewer": "read", "editor": "write", "admin": "admin"}
_MODE_ROLE = {v: k for k, v in ROLE_MODE.items()}

_CALL_MODE: ContextVar[Optional[str]] = ContextVar("veritasgraph_mcp_mode", default=None)
_CALL_ACTOR: ContextVar[str] = ContextVar("veritasgraph_mcp_actor", default="mcp:stdio")


def server_mode() -> str:
    mode = os.getenv("VERITASGRAPH_MCP_MODE", "write").strip().lower()
    return mode if mode in _MODE_RANK else "read"


def effective_mode(cap: Optional[str] = None) -> str:
    """The server mode, lowered to ``cap`` when given (e.g. the caller's role)."""
    mode = server_mode()
    if cap in _MODE_RANK and _MODE_RANK[cap] < _MODE_RANK[mode]:
        return cap  # type: ignore[return-value]
    return mode


def current_mode() -> str:
    return _CALL_MODE.get() or server_mode()


@contextlib.contextmanager
def call_context(mode: str, actor: str = "mcp:stdio") -> Iterator[None]:
    """Run tool handlers as ``mode`` / ``actor`` (works across ``asyncio.to_thread``)."""
    mode_token = _CALL_MODE.set(mode)
    actor_token = _CALL_ACTOR.set(actor)
    try:
        yield
    finally:
        _CALL_MODE.reset(mode_token)
        _CALL_ACTOR.reset(actor_token)


def _role() -> str:
    return _MODE_ROLE[current_mode()]


def _actor() -> str:
    return _CALL_ACTOR.get()


def _default_model() -> str:
    return os.getenv("VERITASGRAPH_MODEL", "qwen3:latest").strip() or "qwen3:latest"


def _engine():
    """Lazily import and return the shared GraphRAG engine singleton."""
    from studio_api.graphrag_engine import engine

    return engine


def _ints(args: dict, **defaults: int) -> Dict[str, int]:
    return {k: int(args.get(k, v)) for k, v in defaults.items()}


def _needs_store(engine: Any) -> Optional[dict]:
    if engine.store is None or engine.ontology is None:
        return {"error": "The graph store is not available."}
    return None


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
        result = _engine().ingest(title, text, model, actor=_actor())
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
    mode = str(args.get("mode", "exploratory") or "exploratory")
    if mode not in ("exploratory", "governed"):
        return {"error": "mode must be exploratory or governed"}
    try:
        limits = _ints(args, max_depth=2, max_nodes=25)
    except (TypeError, ValueError):
        return {"error": "max_depth and max_nodes must be integers"}
    try:
        result = _engine().query(
            question, model, limits["max_depth"], limits["max_nodes"], mode=mode, actor=_actor()
        )
        return pii.redact_answer_payload(result, _role())
    except Exception as exc:  # noqa: BLE001
        log.exception("query_graph failed")
        return {"error": str(exc)}


def handle_check_answerable(args: dict) -> dict:
    """Report whether the graph covers a question, without an LLM call."""
    question = str(args.get("question", "")).strip()
    if not question:
        return {"error": "question is required"}
    mode = str(args.get("mode", "exploratory") or "exploratory")
    if mode not in ("exploratory", "governed"):
        return {"error": "mode must be exploratory or governed"}
    from veritasgraph.answerability import check_answerable

    try:
        return check_answerable(_engine(), question, mode)
    except Exception as exc:  # noqa: BLE001
        log.exception("check_answerable failed")
        return {"error": str(exc)}


def handle_search_entities(args: dict) -> dict:
    """Retrieve the subgraph most relevant to a query (no LLM call)."""
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query is required", "nodes": [], "edges": []}
    try:
        limits = _ints(args, max_depth=2, max_nodes=25)
    except (TypeError, ValueError):
        return {"error": "max_depth and max_nodes must be integers"}
    try:
        ctx = _engine().retrieve(query, max_depth=limits["max_depth"], max_nodes=limits["max_nodes"])
        result = {
            "seeds": ctx.get("seeds", []),
            "nodes": [
                {"id": n["id"], "name": n["name"], "type": n["type"],
                 "description": n["description"], "sources": n.get("sources", []),
                 "pii_flags": n.get("pii_flags", [])}
                for n in ctx.get("nodes", [])
            ],
            "edges": [
                {"id": e["id"], "source": e["source"], "target": e["target"],
                 "description": e["description"], "predicate": e.get("predicate"),
                 "sources": e.get("sources", []), "pii_flags": e.get("pii_flags", [])}
                for e in ctx.get("edges", [])
            ],
            "source_count": len(ctx.get("sources", [])),
        }
        return pii.redact_payload(result, _role())
    except Exception as exc:  # noqa: BLE001
        log.exception("search_entities failed")
        return {"error": str(exc), "nodes": [], "edges": []}


def handle_get_graph(_args: dict) -> dict:
    """Return the full knowledge graph (nodes, edges, and stats)."""
    try:
        return pii.redact_payload(_engine().graph(), _role())
    except Exception as exc:  # noqa: BLE001
        log.exception("get_graph failed")
        return {"error": str(exc)}


def handle_get_entity(args: dict) -> dict:
    """One entity with its neighbours, backing sources and glossary terms."""
    ident = str(args.get("entity", "")).strip()
    if not ident:
        return {"error": "entity is required"}
    found = _engine().entity(ident)
    if found is None:
        return {"error": f"Unknown entity: {ident}"}
    return pii.redact_payload(found, _role())


def handle_get_ontology(_args: dict) -> dict:
    """Entity types, predicates and glossary terms with their status."""
    engine = _engine()
    return _needs_store(engine) or engine.ontology.snapshot()


def handle_search_terms(args: dict) -> dict:
    """Search the business glossary by name, synonym or definition."""
    engine = _engine()
    missing = _needs_store(engine)
    if missing:
        return missing
    try:
        limit = int(args.get("limit", 20))
    except (TypeError, ValueError):
        return {"error": "limit must be an integer"}
    return {"terms": engine.ontology.list_terms(str(args.get("query", "")), max(1, min(limit, 200)))}


def handle_get_term(args: dict) -> dict:
    """One glossary term (by id or name) with its linked entities."""
    engine = _engine()
    missing = _needs_store(engine)
    if missing:
        return missing
    ident = str(args.get("term", "")).strip()
    if not ident:
        return {"error": "term is required"}
    found = engine.ontology.get_term(ident)
    return found if found is not None else {"error": f"Unknown term: {ident}"}


def handle_get_answer_receipt(args: dict) -> dict:
    """The stored receipt of a previous answer: evidence, grounding, feedback."""
    from veritasgraph import governance

    engine = _engine()
    missing = _needs_store(engine)
    if missing:
        return missing
    answer_id = str(args.get("answer_id", "")).strip()
    if not answer_id:
        return {"error": "answer_id is required"}
    found = governance.get_answer(engine.store, answer_id)
    if found is None:
        return {"error": f"Unknown answer: {answer_id}"}
    return pii.redact_answer_payload(found, _role())


def handle_compile_status(_args: dict) -> dict:
    """Last compile run and the number of open curation suggestions."""
    from veritasgraph import compile as compiler

    engine = _engine()
    return _needs_store(engine) or compiler.status(engine.store)


def handle_propose_term(args: dict) -> dict:
    """Propose a glossary term (lands as ``proposed``; an admin certifies it)."""
    from veritasgraph import governance

    engine = _engine()
    missing = _needs_store(engine)
    if missing:
        return missing
    name = str(args.get("name", "")).strip()
    if not name:
        return {"error": "name is required"}
    synonyms = args.get("synonyms") or []
    entity_ids = args.get("entity_ids") or None
    if not isinstance(synonyms, list) or (entity_ids is not None and not isinstance(entity_ids, list)):
        return {"error": "synonyms and entity_ids must be lists"}
    try:
        term = engine.ontology.upsert_term(
            name,
            definition=str(args.get("definition", "")),
            synonyms=[str(s) for s in synonyms],
            entity_ids=[str(e) for e in entity_ids] if entity_ids else None,
            owner_id=_actor(),
        )
    except (KeyError, ValueError) as exc:
        return {"error": str(exc)}
    governance.record_audit(engine.store, _actor(), "ontology.term.upsert", term["id"], {"via": "mcp"})
    return term


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
            actor=_actor(),
        )
        return {"status": "imported", **result}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        log.exception("import_graph failed")
        return {"error": str(exc)}


def handle_clear_graph(_args: dict) -> dict:
    """Delete every node, edge, and source (a snapshot is taken first)."""
    try:
        result = _engine().clear(actor=_actor()) or {}
        return {"status": "cleared", **result}
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
_MODE_PROP = {
    "type": "string",
    "enum": ["exploratory", "governed"],
    "description": (
        "governed: only answer when certified glossary terms cover the question, and "
        "withhold answers whose citations are not in the retrieved evidence."
    ),
}
_LIMIT_PROPS = {
    "max_depth": {"type": "integer", "description": "Max graph hops (default 2)."},
    "max_nodes": {"type": "integer", "description": "Max subgraph nodes (default 25)."},
}

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "veritasgraph_check_answerable",
        "description": (
            "Check whether the knowledge graph covers a question before asking it: "
            "returns matched entities and glossary terms, coverage and a reason. No LLM call."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Natural-language question."},
                "mode": _MODE_PROP,
            },
            "required": ["question"],
        },
        "_handler": handle_check_answerable,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_query",
        "description": (
            "Ask a question and get a graph-grounded, multi-hop answer with "
            "verifiable [doc#chunk] citations, a grounded flag, the reasoning path "
            "and an answer_id receipt. Abstains when the graph has no evidence."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Natural-language question."},
                "model": _MODEL_PROP,
                "mode": _MODE_PROP,
                **_LIMIT_PROPS,
            },
            "required": ["question"],
        },
        "_handler": handle_query_graph,
        "_mode": "read",
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
                **_LIMIT_PROPS,
            },
            "required": ["query"],
        },
        "_handler": handle_search_entities,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_get_entity",
        "description": "One entity (by id or name) with neighbours, source chunks and glossary terms.",
        "inputSchema": {
            "type": "object",
            "properties": {"entity": {"type": "string", "description": "Entity id or name."}},
            "required": ["entity"],
        },
        "_handler": handle_get_entity,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_get_graph",
        "description": "Return the full knowledge graph: all nodes, edges, and stats.",
        "inputSchema": {"type": "object", "properties": {}},
        "_handler": handle_get_graph,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_get_ontology",
        "description": (
            "The governed vocabulary: entity types, predicates (with domain/range) and "
            "glossary terms, each with status proposed / certified / deprecated."
        ),
        "inputSchema": {"type": "object", "properties": {}},
        "_handler": handle_get_ontology,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_search_terms",
        "description": "Search the business glossary by name, synonym or definition.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search for."},
                "limit": {"type": "integer", "description": "Max results (default 20)."},
            },
            "required": ["query"],
        },
        "_handler": handle_search_terms,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_get_term",
        "description": "One glossary term (by id or name) with its definition, synonyms, status and linked entities.",
        "inputSchema": {
            "type": "object",
            "properties": {"term": {"type": "string", "description": "Term id or name."}},
            "required": ["term"],
        },
        "_handler": handle_get_term,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_get_answer_receipt",
        "description": (
            "Fetch the receipt for a previous answer_id: evidence ids, grounding, the "
            "graph version it used, whether the graph changed since, and feedback."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"answer_id": {"type": "string", "description": "The answer_id from veritasgraph_query."}},
            "required": ["answer_id"],
        },
        "_handler": handle_get_answer_receipt,
        "_mode": "read",
    },
    {
        "name": "veritasgraph_compile_status",
        "description": "Last ontology compile run and the number of open curation suggestions.",
        "inputSchema": {"type": "object", "properties": {}},
        "_handler": handle_compile_status,
        "_mode": "read",
    },
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
        "_mode": "write",
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
        "_mode": "write",
    },
    {
        "name": "veritasgraph_propose_term",
        "description": (
            "Propose a business glossary term (status 'proposed' until an admin "
            "certifies it), optionally linked to entity ids."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Term name."},
                "definition": {"type": "string", "description": "Plain-language definition."},
                "synonyms": {"type": "array", "items": {"type": "string"}},
                "entity_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name"],
        },
        "_handler": handle_propose_term,
        "_mode": "write",
    },
    {
        "name": "veritasgraph_clear_graph",
        "description": "Clear the entire knowledge graph (destructive; a snapshot is taken first).",
        "inputSchema": {"type": "object", "properties": {}},
        "_handler": handle_clear_graph,
        "_mode": "admin",
    },
]

TOOL_MODES: Dict[str, str] = {t["name"]: t["_mode"] for t in TOOL_DEFINITIONS}


def tool_allowed(name: str, mode: Optional[str] = None) -> bool:
    need = TOOL_MODES.get(name)
    return need is not None and _MODE_RANK[need] <= _MODE_RANK[mode or current_mode()]


def public_tools(mode: Optional[str] = None) -> List[Dict[str, Any]]:
    """Handler-free tool definitions visible at ``mode``."""
    return [
        {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
        for t in TOOL_DEFINITIONS
        if tool_allowed(t["name"], mode)
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
    {
        "uri": "veritasgraph://ontology",
        "name": "VeritasGraph ontology",
        "description": "Entity types, predicates and glossary terms with their status.",
        "mimeType": "application/json",
    },
]


def handle_resource_read(uri: str) -> Dict[str, Any]:
    """Resolve a ``veritasgraph://`` resource URI to its JSON text payload."""
    uri = (uri or "").strip()
    if uri == "veritasgraph://graph":
        payload: Any = pii.redact_payload(_engine().graph(), _role())
    elif uri == "veritasgraph://stats":
        payload = _engine().graph().get("stats", {})
    elif uri == "veritasgraph://ontology":
        payload = handle_get_ontology({})
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

SERVER_INSTRUCTIONS = (
    "VeritasGraph answers questions from a local knowledge graph with verifiable "
    "citations. Before answering a factual question, call veritasgraph_check_answerable; "
    "if it is not answerable, say so instead of guessing. Use veritasgraph_query and "
    "quote its [doc#chunk] citations; treat answers with grounded=false or abstained=true "
    "as unverified. Use mode='governed' when the user needs answers restricted to "
    "certified business terms. Glossary terms and types are in veritasgraph_get_ontology."
)
