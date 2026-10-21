"""Unit tests for eval.rag.metrics — pure, offline, no LLM/Ollama required.

Fixtures with hand-computed expected values live in ``tests/rag/fixtures``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.rag import metrics

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# normalize_answer
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("The Quick, Brown Fox!", "quick brown fox"),
        ("A an the", ""),
        ("  Multiple   spaces  ", "multiple spaces"),
        ("1987", "1987"),
        (None, ""),
    ],
)
def test_normalize_answer(raw, expected):
    assert metrics.normalize_answer(raw) == expected


# --------------------------------------------------------------------------- #
# exact_match
# --------------------------------------------------------------------------- #
def test_exact_match_true_despite_formatting():
    assert metrics.exact_match("The answer is 1987.", "1987.") == 0.0  # extra words
    assert metrics.exact_match("John Doe", "john doe") == 1.0
    assert metrics.exact_match("the  Lisbon", "Lisbon") == 1.0


def test_exact_match_false():
    assert metrics.exact_match("Madrid", "Lisbon") == 0.0


# --------------------------------------------------------------------------- #
# token_f1
# --------------------------------------------------------------------------- #
def test_token_f1_perfect():
    assert metrics.token_f1("John Doe", "john doe") == pytest.approx(1.0)


def test_token_f1_partial():
    # pred tokens: {the, engineer, is, john, doe} (the removed) -> {engineer, is, john, doe}
    # gold tokens: {john, doe}
    f1 = metrics.token_f1("The engineer is John Doe", "John Doe")
    assert 0.0 < f1 < 1.0
    assert f1 == pytest.approx(2 * (2 / 4) * (2 / 2) / ((2 / 4) + (2 / 2)))


def test_token_f1_no_overlap():
    assert metrics.token_f1("Madrid", "Lisbon") == 0.0


def test_token_f1_both_empty():
    assert metrics.token_f1("the a an", "") == 1.0


def test_token_f1_one_empty():
    assert metrics.token_f1("Lisbon", "") == 0.0


# --------------------------------------------------------------------------- #
# citation precision / recall / f1
# --------------------------------------------------------------------------- #
def test_citation_precision_recall_perfect():
    cited = ["doc_phoenix#0", "doc_patent#2"]
    gold = ["doc_phoenix#0", "doc_patent#2"]
    assert metrics.citation_precision(cited, gold) == 1.0
    assert metrics.citation_recall(cited, gold) == 1.0
    assert metrics.citation_f1(cited, gold) == 1.0


def test_citation_precision_with_extra_citation():
    cited = ["doc_bridge#1", "doc_town#0"]
    gold = ["doc_bridge#1"]
    assert metrics.citation_precision(cited, gold) == 0.5
    assert metrics.citation_recall(cited, gold) == 1.0


def test_citation_no_citations():
    assert metrics.citation_precision([], ["doc_acme#0"]) == 0.0
    assert metrics.citation_recall([], ["doc_acme#0"]) == 0.0
    assert metrics.citation_f1([], ["doc_acme#0"]) == 0.0


def test_citation_empty_gold_is_recall_one():
    assert metrics.citation_recall(["x"], []) == 1.0


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #
def test_aggregate_basic():
    agg = metrics.aggregate([1.0, 0.0, 1.0, 0.0])
    assert agg["mean"] == pytest.approx(0.5)
    assert agg["n"] == 4
    assert agg["std"] >= 0.0


def test_aggregate_empty():
    agg = metrics.aggregate([])
    assert agg == {"mean": 0.0, "std": 0.0, "n": 0}


def test_mean_over_seeds_sample_std():
    agg = metrics.mean_over_seeds([0.40, 0.42, 0.44])
    assert agg["mean"] == pytest.approx(0.42)
    assert agg["n"] == 3
    assert agg["std"] > 0.0


# --------------------------------------------------------------------------- #
# fixture-driven end-to-end metric check
# --------------------------------------------------------------------------- #
def test_fixtures_expected_values():
    gold_records = {r["id"]: r for r in _load("hotpot_mini.json")["records"]}
    preds = _load("answers_mini.json")["predictions"]

    for pred in preds:
        rec = gold_records[pred["id"]]
        exp = pred["expected"]

        em = metrics.exact_match(pred["answer"], rec["answer"])
        assert em == exp["em"], f"EM mismatch for {pred['id']}"

        cit_p = metrics.citation_precision(pred["cited"], rec["supporting_facts"])
        cit_r = metrics.citation_recall(pred["cited"], rec["supporting_facts"])
        assert cit_p == pytest.approx(exp["cit_p"]), f"cit_p mismatch for {pred['id']}"
        assert cit_r == pytest.approx(exp["cit_r"]), f"cit_r mismatch for {pred['id']}"

        f1 = metrics.token_f1(pred["answer"], rec["answer"])
        if "f1" in exp:
            assert f1 == pytest.approx(exp["f1"]), f"F1 mismatch for {pred['id']}"
        if "f1_gt" in exp:
            assert f1 >= exp["f1_gt"], f"F1 lower bound failed for {pred['id']}"
