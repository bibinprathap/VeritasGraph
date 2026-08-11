"""Normalization + graph + risk tests."""

from __future__ import annotations

from clinical_kg import normalize, risk
from clinical_kg.models import (
    AFFIRMED,
    CERTAIN,
    RECENT,
    PATIENT,
    Assertion,
    Concept,
    Span,
)
from clinical_kg.graph import KnowledgeGraph


def test_normalize_condition_codes():
    concept, icd10 = normalize.normalize_condition("T2DM")
    assert concept.system == "SNOMED"
    assert concept.code == "44054006"
    assert icd10 == "E11.9"


def test_normalize_medication_and_lab():
    assert normalize.normalize_medication("glucophage").code == "6809"
    assert normalize.normalize_lab("a1c").code == "4548-4"


def _mk_assertion(code, system, display, label, **ctx):
    concept = Concept(system, code, display)
    span = Span("doc-1", 0, "problem_list", 0, 5, display)
    return Assertion(
        concept=concept, label=label,
        negation=ctx.get("negation", AFFIRMED),
        certainty=CERTAIN, temporality=RECENT, experiencer=PATIENT,
        evidence=[span], attributes=ctx.get("attributes", {}),
    )


def test_graph_adds_facts_with_provenance():
    kg = KnowledgeGraph()
    kg.add_encounter("P1", "doc-1", "2025-01-01", "note")
    kg.add_assertion("P1", _mk_assertion("44054006", "SNOMED", "Type 2 diabetes mellitus", "CONDITION"))
    facts = kg.facts_for("P1")
    assert len(facts) == 1
    assert facts[0]["display"] == "Type 2 diabetes mellitus"
    assert facts[0]["citations"] == ["[doc-1#0]"]


def test_graph_cytoscape_export():
    kg = KnowledgeGraph()
    kg.add_assertion("P1", _mk_assertion("6809", "RxNorm", "Metformin", "MEDICATION"))
    cyto = kg.cytoscape("P1")
    assert cyto["nodes"]
    assert any(n["data"]["ntype"] == "Medication" for n in cyto["nodes"])


def test_k_anonymity():
    records = [
        {"zip3": "021", "age_band": "60-70", "sex": "M"},
        {"zip3": "021", "age_band": "60-70", "sex": "M"},
        {"zip3": "021", "age_band": "60-70", "sex": "M"},
        {"zip3": "980", "age_band": "40-50", "sex": "F"},
    ]
    report = risk.k_anonymity(records, ["zip3", "age_band", "sex"], target_k=2)
    assert report.k == 1
    assert report.satisfied is False
    assert len(report.violating_groups) == 1
    assert report.violating_groups[0]["size"] == 1
