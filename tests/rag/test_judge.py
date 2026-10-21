"""Unit tests for eval.rag.judge — LLM-as-judge parsing & scoring (mocked LLM)."""

from __future__ import annotations

from typing import Dict, List

import pytest

from eval.rag import judge


def _answer(text: str, citations=None):
    return {
        "answer": text,
        "citations": citations or [],
        "reasoning_path": [],
        "subgraph": {"nodes": [], "edges": []},
    }


# --------------------------------------------------------------------------- #
# _parse_score
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"score": 0.8}', 0.8),
        ('{"score": 1}', 1.0),
        ("The score is 0.42 overall.", 0.42),
        ("8", 0.8),       # 0..10 rubric tolerated
        ("0", 0.0),
        ('{"score": 1.5}', 1.0),   # clamped
        ('{"score": -0.2}', 0.0),  # clamped
    ],
)
def test_parse_score(raw, expected):
    assert judge._parse_score(raw) == pytest.approx(expected)


def test_parse_score_empty_raises():
    with pytest.raises(ValueError):
        judge._parse_score("")


def test_parse_score_no_number_raises():
    with pytest.raises(ValueError):
        judge._parse_score("no numbers here")


# --------------------------------------------------------------------------- #
# judge metrics with a fake chat
# --------------------------------------------------------------------------- #
def make_chat(responses: List[str]):
    calls = {"n": 0}

    def _chat(model: str, messages: List[Dict[str, str]], temperature: float) -> str:
        i = min(calls["n"], len(responses) - 1)
        calls["n"] += 1
        return responses[i]

    _chat.calls = calls  # type: ignore[attr-defined]
    return _chat


def test_comprehensiveness_parses_json():
    chat = make_chat(['{"score": 0.7}'])
    score = judge.comprehensiveness("q", _answer("detailed answer"), model="m", chat=chat)
    assert score == pytest.approx(0.7)


def test_diversity_parses_number():
    chat = make_chat(["Diversity rating: 0.55"])
    score = judge.diversity("q", _answer("varied answer"), model="m", chat=chat)
    assert score == pytest.approx(0.55)


def test_judge_retries_on_garbage_then_succeeds():
    chat = make_chat(["totally unparseable", '{"score": 0.9}'])
    score = judge.comprehensiveness("q", _answer("a"), model="m", chat=chat)
    assert score == pytest.approx(0.9)
    assert chat.calls["n"] == 2  # retried once


def test_citation_faithfulness_no_citations_is_zero():
    chat = make_chat(['{"score": 1.0}'])
    score = judge.citation_faithfulness(_answer("claim", citations=[]), model="m", chat=chat)
    assert score == 0.0
    assert chat.calls["n"] == 0  # short-circuits, no LLM call


def test_citation_faithfulness_with_citations():
    chat = make_chat(['{"score": 0.85}'])
    ans = _answer(
        "John Doe holds the patent. [doc_patent#2]",
        citations=[{"id": "doc_patent#2", "title": "Patent", "text": "John Doe ... patent"}],
    )
    score = judge.citation_faithfulness(ans, model="m", chat=chat)
    assert score == pytest.approx(0.85)
