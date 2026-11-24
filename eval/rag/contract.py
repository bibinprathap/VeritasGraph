"""The shared answer contract used across every system adapter.

The whole harness is system-agnostic because every adapter — naive vector RAG,
Microsoft GraphRAG, and VeritasGraph — returns the exact same dict shape. That
shape is the real return value of
``studio_api.graphrag_engine.GraphRAGEngine.query()``:

    {
        "answer": str,
        "citations": [{"id": str, "title": str, "text": str}, ...],
        "reasoning_path": [str, ...],
        "subgraph": {"nodes": [...], "edges": [...]},
    }

Baselines without a graph return ``reasoning_path=[]`` and an empty ``subgraph``.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class Citation(TypedDict):
    """A single cited source chunk (the provenance key is ``id``)."""

    id: str  # e.g. "doc_ab12cd34#0"
    title: str
    text: str


class Subgraph(TypedDict):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class Answer(TypedDict):
    """The uniform shape every system adapter must return."""

    answer: str
    citations: List[Citation]
    reasoning_path: List[str]
    subgraph: Subgraph


_REQUIRED_KEYS = ("answer", "citations", "reasoning_path", "subgraph")


def empty_subgraph() -> Subgraph:
    """A subgraph placeholder for systems that have no graph (e.g. naive RAG)."""
    return {"nodes": [], "edges": []}


def validate_answer(obj: Any) -> Answer:
    """Validate and lightly normalise an object against the :class:`Answer` contract.

    Raises ``ValueError`` describing the first violation. On success returns the
    object (same instance) typed as :class:`Answer`. This is the single gate used
    by both the runner and ``tests/rag/test_contract.py``.
    """
    if not isinstance(obj, dict):
        raise ValueError(f"answer must be a dict, got {type(obj).__name__}")

    for key in _REQUIRED_KEYS:
        if key not in obj:
            raise ValueError(f"answer is missing required key: {key!r}")

    if not isinstance(obj["answer"], str):
        raise ValueError("'answer' must be a str")

    citations = obj["citations"]
    if not isinstance(citations, list):
        raise ValueError("'citations' must be a list")
    for i, cit in enumerate(citations):
        if not isinstance(cit, dict):
            raise ValueError(f"citations[{i}] must be a dict")
        for ck in ("id", "title", "text"):
            if ck not in cit:
                raise ValueError(f"citations[{i}] missing key {ck!r}")
            if not isinstance(cit[ck], str):
                raise ValueError(f"citations[{i}][{ck!r}] must be a str")

    if not isinstance(obj["reasoning_path"], list):
        raise ValueError("'reasoning_path' must be a list")
    if not all(isinstance(step, str) for step in obj["reasoning_path"]):
        raise ValueError("'reasoning_path' must be a list of str")

    subgraph = obj["subgraph"]
    if not isinstance(subgraph, dict):
        raise ValueError("'subgraph' must be a dict")
    for sk in ("nodes", "edges"):
        if sk not in subgraph:
            raise ValueError(f"subgraph missing key {sk!r}")
        if not isinstance(subgraph[sk], list):
            raise ValueError(f"subgraph[{sk!r}] must be a list")

    return obj  # type: ignore[return-value]


def cited_ids(answer: Answer) -> List[str]:
    """The ordered, de-duplicated list of source ids this answer cites."""
    seen: Dict[str, None] = {}
    for cit in answer["citations"]:
        seen.setdefault(cit["id"], None)
    return list(seen.keys())
