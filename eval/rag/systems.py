"""System adapters — three callables with one shared signature.

Each adapter answers a question and returns the uniform :class:`Answer` dict
(see ``eval.rag.contract``), so the metrics code is system-agnostic:

* :func:`naive_rag`     — FAISS-style top-k over TextUnits + the shared LLM.
* :func:`msrag`         — Microsoft GraphRAG GlobalSearch (pinned), normalised.
* :func:`veritasgraph`  — ``GraphRAGEngine.query()`` (already the right shape).

The adapters take their retrieval backends as explicit arguments so they are
fully unit-testable with fakes (no FAISS, no Ollama, no Neo4j required).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence

from .contract import Answer, Citation, empty_subgraph, validate_answer
from .llm import ChatFn, ollama_chat


# --------------------------------------------------------------------------- #
# Retrieval backends (duck-typed; real impls live in run.py / index builders)
# --------------------------------------------------------------------------- #
class Chunk(Protocol):
    id: str
    title: str
    text: str


class VectorIndex(Protocol):
    def search(self, query: str, k: int) -> Sequence[Chunk]:
        ...


def _chunks_to_citations(chunks: Sequence[Chunk]) -> List[Citation]:
    return [{"id": c.id, "title": c.title, "text": c.text} for c in chunks]


def _naive_prompt(question: str, chunks: Sequence[Chunk]) -> List[Dict[str, str]]:
    sources = "\n\n".join(f"[{c.id}] {c.title}: {c.text}" for c in chunks)
    system = (
        "You answer the question using ONLY the provided sources. Cite the source "
        "id(s) you rely on in square brackets, e.g. [id]. If the sources are "
        "insufficient, say so explicitly."
    )
    user = f"SOURCES:\n{sources}\n\nQUESTION: {question}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# --------------------------------------------------------------------------- #
# Adapter 1 — Naive vector RAG (baseline)
# --------------------------------------------------------------------------- #
def naive_rag(
    question: str,
    *,
    index: VectorIndex,
    model: str,
    top_k: int = 8,
    temperature: float = 0.0,
    chat: ChatFn = ollama_chat,
) -> Answer:
    """Top-k vector retrieval over TextUnits, answered by the shared LLM."""
    chunks = list(index.search(question, top_k))
    text = chat(model, _naive_prompt(question, chunks), temperature)
    answer: Answer = {
        "answer": text,
        "citations": _chunks_to_citations(chunks),
        "reasoning_path": [],
        "subgraph": empty_subgraph(),
    }
    return validate_answer(answer)


# --------------------------------------------------------------------------- #
# Adapter 2 — Microsoft GraphRAG GlobalSearch (baseline)
# --------------------------------------------------------------------------- #
def msrag(
    question: str,
    *,
    search: Callable[[str], Dict[str, Any]],
) -> Answer:
    """Normalise a ``microsoft/graphrag`` GlobalSearch result to the contract.

    ``search(question)`` is expected to return a dict with at least ``response``
    and ``context`` (the community reports it used). We map those to the uniform
    shape; MSRAG has no fine-grained graph path, so ``reasoning_path`` is empty
    and ``citations`` point at the community-report ids it surfaced.
    """
    result = search(question)
    response = str(result.get("response", ""))
    context = result.get("context", []) or []

    citations: List[Citation] = []
    for item in context:
        cid = str(item.get("id", ""))
        if not cid:
            continue
        citations.append(
            {
                "id": cid,
                "title": str(item.get("title", "community report")),
                "text": str(item.get("text", "")),
            }
        )

    answer: Answer = {
        "answer": response,
        "citations": citations,
        "reasoning_path": [],
        "subgraph": empty_subgraph(),
    }
    return validate_answer(answer)


# --------------------------------------------------------------------------- #
# Adapter 3 — VeritasGraph (ours)
# --------------------------------------------------------------------------- #
class _QueryEngine(Protocol):
    def query(
        self, question: str, model: str, max_depth: int, max_nodes: int
    ) -> Dict[str, Any]:
        ...


def veritasgraph(
    question: str,
    *,
    engine: Optional[_QueryEngine] = None,
    model: str,
    max_depth: int = 2,
    max_nodes: int = 25,
) -> Answer:
    """Wrap ``GraphRAGEngine.query()`` — already returns the contract shape."""
    if engine is None:
        from studio_api.graphrag_engine import engine as _default_engine

        engine = _default_engine
    result = engine.query(question, model, max_depth, max_nodes)
    return validate_answer(result)
