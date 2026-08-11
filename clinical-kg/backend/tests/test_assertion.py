"""Assertion reconciliation + contradiction detection tests."""

from __future__ import annotations

from clinical_kg import assertion, extract


def _assertion_for(assertions, code):
    return [a for a in assertions if a.concept.code == code][0]


def test_contradiction_across_sections():
    note = """HPI: Patient denies any history of diabetes.
Problem List:
1. Type 2 diabetes mellitus, on metformin 500mg BID.
"""
    ents = extract.extract(note, "note-x")
    assertions = assertion.reconcile(ents)
    dm = _assertion_for(assertions, "44054006")
    # Problem List (authority 4) beats HPI (authority 3) -> affirmed.
    assert dm.negation == "affirmed"
    # But the disagreement is surfaced as a contradiction with both spans.
    assert dm.contradiction is True
    sections = {s.section for s in dm.conflicting_spans}
    assert "hpi" in sections and "problem_list" in sections


def test_no_contradiction_when_consistent():
    note = """Problem List:
1. Type 2 diabetes mellitus.
Assessment and Plan: Type 2 diabetes mellitus, continue metformin.
"""
    ents = extract.extract(note, "n")
    dm = _assertion_for(assertion.reconcile(ents), "44054006")
    assert dm.contradiction is False
    assert dm.negation == "affirmed"


def test_section_authority_wins():
    # Negated in low-authority HPI, affirmed in high-authority A/P.
    note = """HPI: no diabetes.
Assessment and Plan: Type 2 diabetes mellitus.
"""
    ents = extract.extract(note, "n")
    dm = _assertion_for(assertion.reconcile(ents), "44054006")
    assert dm.negation == "affirmed"


def test_grouping_by_concept():
    note = "metformin 500mg BID. Later: metformin 1000mg daily."
    ents = extract.extract(note, "n")
    assertions = assertion.reconcile(ents)
    metformin = [a for a in assertions if a.concept.code == "6809"]
    assert len(metformin) == 1  # both mentions merged into one assertion
    assert len(metformin[0].evidence) == 2
