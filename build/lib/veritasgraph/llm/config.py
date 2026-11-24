"""Model endpoint configuration from ``VG_*`` environment variables.

Roles: ``reasoning`` (SQL generation, compilation), ``fast`` (routing, answer
prose; falls back to the reasoning settings), ``embed`` and ``rerank``.
Every role defaults to a local Ollama; an API key is optional.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
ROLES = ("reasoning", "fast", "embed", "rerank")
RERANK_MODES = ("none", "rerank-api", "tei", "local")

_PREFIX = {"reasoning": "VG_LLM", "fast": "VG_LLM_FAST", "embed": "VG_EMBED", "rerank": "VG_RERANK"}
_FALLBACK = {"fast": "VG_LLM"}
_DEFAULT_MODEL = {
    "reasoning": "qwen2.5-coder-32b-8k",
    "fast": "qwen2.5-coder-32b-8k",
    "embed": "nomic-embed-text",
    "rerank": "BAAI/bge-reranker-v2-m3",
}
# Models that expect task prefixes instead of an input-type field.
_KNOWN_PREFIXES: Dict[str, Tuple[str, str]] = {
    "nomic-embed-text": ("search_query: ", "search_document: "),
    "mxbai-embed-large": ("Represent this sentence for searching relevant passages: ", ""),
    "snowflake-arctic-embed": ("Represent this sentence for searching relevant passages: ", ""),
    "bge-m3": ("", ""),
    "all-minilm": ("", ""),
}


@dataclass(frozen=True)
class Endpoint:
    role: str
    base_url: str
    model: str
    api_key: Optional[str] = None
    timeout_s: float = 120.0
    extra_body: Dict[str, Any] = field(default_factory=dict)


def _lookup(role: str, name: str) -> Optional[str]:
    for prefix in (_PREFIX[role], _FALLBACK.get(role)):
        if prefix:
            value = os.environ.get(f"{prefix}_{name}", "").strip()
            if value:
                return value
    return None


def endpoint(role: str) -> Endpoint:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    extra_raw = _lookup(role, "EXTRA_BODY") or "{}"
    try:
        extra = json.loads(extra_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{_PREFIX[role]}_EXTRA_BODY is not valid JSON") from exc
    if not isinstance(extra, dict):
        raise RuntimeError(f"{_PREFIX[role]}_EXTRA_BODY must be a JSON object")
    return Endpoint(
        role=role,
        base_url=(_lookup(role, "BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
        model=_lookup(role, "MODEL") or _DEFAULT_MODEL[role],
        api_key=_lookup(role, "API_KEY"),
        timeout_s=float(_lookup(role, "TIMEOUT_S") or 120),
        extra_body=extra,
    )


def embed_prefixes(model: str) -> Tuple[str, str]:
    """(query_prefix, document_prefix). Env vars win, including an explicit empty string."""
    base = model.split(":", 1)[0]
    query, doc = _KNOWN_PREFIXES.get(base, ("", ""))
    if "VG_EMBED_QUERY_PREFIX" in os.environ:
        query = os.environ["VG_EMBED_QUERY_PREFIX"]
    if "VG_EMBED_DOC_PREFIX" in os.environ:
        doc = os.environ["VG_EMBED_DOC_PREFIX"]
    return query, doc


def rerank_mode() -> str:
    mode = os.environ.get("VG_RERANK_MODE", "none").strip().lower()
    if mode not in RERANK_MODES:
        raise RuntimeError(f"VG_RERANK_MODE must be one of {RERANK_MODES}")
    return mode
