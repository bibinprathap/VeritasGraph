"""Unit tests for eval.rag.datasets — offline loaders over fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.rag import datasets

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# --------------------------------------------------------------------------- #
# HotpotQA (fixture uses the normalised schema)
# --------------------------------------------------------------------------- #
def test_load_hotpotqa_fixture():
    recs = datasets.load_hotpotqa(FIXTURES / "hotpot_mini.json")
    assert len(recs) == 3
    first = recs[0]
    assert first.id == "q1"
    assert first.answer == "John Doe"
    assert first.supporting_facts == ["doc_phoenix#0", "doc_patent#2"]


def test_load_hotpotqa_deterministic_subsample():
    a = datasets.load_hotpotqa(FIXTURES / "hotpot_mini.json", limit=2, seed=7)
    b = datasets.load_hotpotqa(FIXTURES / "hotpot_mini.json", limit=2, seed=7)
    assert [r.id for r in a] == [r.id for r in b]
    assert len(a) == 2


def test_normalise_official_hotpot_schema():
    raw = {
        "_id": "x1",
        "question": "q?",
        "answer": "a",
        "supporting_facts": [["Doc A", 0], ["Doc B", 2]],
        "context": [["Doc A", ["s0", "s1"]], ["Doc B", ["s0", "s1", "s2"]]],
    }
    rec = datasets._normalise_hotpot_record(raw)
    assert rec.id == "x1"
    assert rec.supporting_facts == ["Doc A::0", "Doc B::2"]
    assert rec.context_docs["Doc A"] == ["s0", "s1"]


def test_fact_id():
    assert datasets.fact_id("Title", 3) == "Title::3"


# --------------------------------------------------------------------------- #
# Behind the Tech
# --------------------------------------------------------------------------- #
def test_load_behindthetech_json_fixture():
    corpus = datasets.load_behindthetech(FIXTURES / "behindthetech_mini.json")
    assert len(corpus.documents) == 2
    assert corpus.documents[0][0] == "episode_1"
    assert len(corpus.queries) == 2


def test_load_behindthetech_limit():
    corpus = datasets.load_behindthetech(
        FIXTURES / "behindthetech_mini.json", limit=1
    )
    assert len(corpus.documents) == 1


def test_load_behindthetech_dir(tmp_path: Path):
    (tmp_path / "a.txt").write_text("alpha transcript", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta transcript", encoding="utf-8")
    corpus = datasets.load_behindthetech(tmp_path)
    assert {t for t, _ in corpus.documents} == {"a", "b"}
    assert corpus.queries  # default queries applied


def test_load_behindthetech_missing_path():
    with pytest.raises(FileNotFoundError):
        datasets.load_behindthetech("/no/such/path")
