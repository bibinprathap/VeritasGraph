"""TC-12 — Scenario corpus integrity.

The versioned corpus ``scenarios/scenarios.jsonl`` must match the in-memory
``SCENARIOS`` used to compute every published result, so a reviewer who reads
the corpus sees exactly what was evaluated (R1-1, R2-5).
"""

from __future__ import annotations

import json
import os

from medtrust.benchmark import SCENARIOS

CORPUS = os.path.join(os.path.dirname(__file__), "..", "scenarios", "scenarios.jsonl")

EXPECTED_CATEGORIES = {
    "clinical_qa", "pharmacovigilance", "trial_access",
    "phi_handling", "prompt_injection", "privilege_escalation",
}


def _load_corpus():
    rows = []
    with open(CORPUS) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_corpus_file_exists_and_is_nonempty():
    rows = _load_corpus()
    assert len(rows) == 40


def test_corpus_matches_runtime_scenarios():
    rows = _load_corpus()
    corpus_ids = {r["scenario_id"] for r in rows}
    runtime_ids = {s.scenario_id for s in SCENARIOS}
    assert corpus_ids == runtime_ids
    assert len(corpus_ids) == len(SCENARIOS) == 40


def test_corpus_categories_are_complete():
    rows = _load_corpus()
    cats = {r["category"] for r in rows}
    assert cats == EXPECTED_CATEGORIES


def test_corpus_category_per_id_matches_runtime():
    rows = _load_corpus()
    by_id = {r["scenario_id"]: r["category"] for r in rows}
    for s in SCENARIOS:
        assert by_id[s.scenario_id] == s.category
