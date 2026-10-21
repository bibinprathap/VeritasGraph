"""Unit tests for eval.rag.systems — adapters obey the Answer contract (mocked LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from eval.rag import contract
from eval.rag import systems


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
@dataclass
class FakeChunk:
    id: str
    title: str
    text: str


class FakeIndex:
    def __init__(self, chunks: Sequence[FakeChunk]):
        self._chunks = list(chunks)

    def search(self, query: str, k: int):
        return self._chunks[:k]


def fake_chat(model: str, messages: List[Dict[str, str]], temperature: float) -> str:
    # Echo a deterministic answer citing the first source id in the prompt.
    user = messages[-1]["content"]
    return f"Answer derived from sources. {user[:0]}[doc_a#0]"


class FakeEngine:
    def query(self, question, model, max_depth, max_nodes):
        return {
            "answer": "John Doe holds the patent. [doc_patent#2]",
            "citations": [{"id": "doc_patent#2", "title": "Patent", "text": "..."}],
            "reasoning_path": ["Phoenix --[employs]--> John Doe"],
            "subgraph": {"nodes": [{"id": "n1"}], "edges": []},
        }


# --------------------------------------------------------------------------- #
# naive_rag
# --------------------------------------------------------------------------- #
def test_naive_rag_returns_valid_answer():
    index = FakeIndex([FakeChunk("doc_a#0", "A", "alpha"), FakeChunk("doc_b#1", "B", "beta")])
    ans = systems.naive_rag(
        "what is alpha?", index=index, model="m", top_k=2, chat=fake_chat
    )
    contract.validate_answer(ans)
    assert ans["reasoning_path"] == []
    assert ans["subgraph"] == {"nodes": [], "edges": []}
    assert [c["id"] for c in ans["citations"]] == ["doc_a#0", "doc_b#1"]


def test_naive_rag_respects_top_k():
    index = FakeIndex([FakeChunk(f"doc#{i}", str(i), "t") for i in range(10)])
    ans = systems.naive_rag("q", index=index, model="m", top_k=3, chat=fake_chat)
    assert len(ans["citations"]) == 3


# --------------------------------------------------------------------------- #
# msrag
# --------------------------------------------------------------------------- #
def test_msrag_normalises_global_search():
    def fake_search(question: str):
        return {
            "response": "The main themes are AI and society.",
            "context": [
                {"id": "community_0", "title": "Report 0", "text": "..."},
                {"id": "community_1", "title": "Report 1", "text": "..."},
            ],
        }

    ans = systems.msrag("themes?", search=fake_search)
    contract.validate_answer(ans)
    assert ans["answer"].startswith("The main themes")
    assert [c["id"] for c in ans["citations"]] == ["community_0", "community_1"]
    assert ans["reasoning_path"] == []


def test_msrag_handles_empty_context():
    ans = systems.msrag("q", search=lambda q: {"response": "x", "context": []})
    contract.validate_answer(ans)
    assert ans["citations"] == []


# --------------------------------------------------------------------------- #
# veritasgraph
# --------------------------------------------------------------------------- #
def test_veritasgraph_wraps_engine():
    ans = systems.veritasgraph(
        "who holds the patent?", engine=FakeEngine(), model="m", max_depth=2, max_nodes=25
    )
    contract.validate_answer(ans)
    assert ans["reasoning_path"]  # graph system has a path
    assert ans["citations"][0]["id"] == "doc_patent#2"
