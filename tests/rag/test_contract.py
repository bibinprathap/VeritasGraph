"""Unit tests for eval.rag.contract — the shared Answer shape every adapter returns."""

from __future__ import annotations

import pytest

from eval.rag import contract


def _valid_answer() -> dict:
    return {
        "answer": "John Doe holds Patent XYZ. [doc_patent#2]",
        "citations": [
            {"id": "doc_phoenix#0", "title": "Project Phoenix", "text": "..."},
            {"id": "doc_patent#2", "title": "Patent XYZ", "text": "..."},
        ],
        "reasoning_path": ["Project Phoenix --[employs]--> John Doe"],
        "subgraph": {"nodes": [{"id": "n1"}], "edges": []},
    }


def test_validate_valid_answer_passes():
    ans = contract.validate_answer(_valid_answer())
    assert ans["answer"].startswith("John Doe")


def test_baseline_shape_with_empty_graph_is_valid():
    ans = {
        "answer": "1987",
        "citations": [{"id": "doc_bridge#1", "title": "Bridge", "text": "..."}],
        "reasoning_path": [],
        "subgraph": contract.empty_subgraph(),
    }
    assert contract.validate_answer(ans) is ans


@pytest.mark.parametrize("missing", ["answer", "citations", "reasoning_path", "subgraph"])
def test_missing_required_key_raises(missing):
    ans = _valid_answer()
    del ans[missing]
    with pytest.raises(ValueError, match=missing):
        contract.validate_answer(ans)


def test_non_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        contract.validate_answer(["not", "a", "dict"])


def test_bad_citation_missing_field_raises():
    ans = _valid_answer()
    ans["citations"][0].pop("text")
    with pytest.raises(ValueError, match="text"):
        contract.validate_answer(ans)


def test_reasoning_path_must_be_str_list():
    ans = _valid_answer()
    ans["reasoning_path"] = [123]
    with pytest.raises(ValueError, match="reasoning_path"):
        contract.validate_answer(ans)


def test_subgraph_missing_edges_raises():
    ans = _valid_answer()
    ans["subgraph"] = {"nodes": []}
    with pytest.raises(ValueError, match="edges"):
        contract.validate_answer(ans)


def test_cited_ids_dedup_preserves_order():
    ans = _valid_answer()
    ans["citations"].append(
        {"id": "doc_phoenix#0", "title": "dup", "text": "..."}
    )
    assert contract.cited_ids(ans) == ["doc_phoenix#0", "doc_patent#2"]
