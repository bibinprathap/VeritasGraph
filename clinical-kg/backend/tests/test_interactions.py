"""Tests for the drug-drug interaction (DDI) enrichment layer."""

from __future__ import annotations

from clinical_kg import interactions as ddi
from clinical_kg.models import Document
from clinical_kg.pipeline import Pipeline


# -- reference table ------------------------------------------------------
def test_interaction_lookup_is_order_independent():
    a = ddi.interaction_for("11289", "1191")  # warfarin + aspirin
    b = ddi.interaction_for("1191", "11289")
    assert a is not None and a is b
    assert a.severity == "major"


def test_unknown_pair_returns_none():
    assert ddi.interaction_for("6809", "6809") is None  # metformin + metformin
    assert ddi.interaction_for("29046", "83367") is None  # lisinopril + atorvastatin


def test_side_effects_lookup():
    assert "Bleeding" in ddi.side_effects_for("11289")  # warfarin
    assert ddi.side_effects_for("nonexistent") == []


# -- graph enrichment + patient query -------------------------------------
def _pipeline_with(text: str, patient_id="PX", doc_id="note-x") -> Pipeline:
    p = Pipeline()
    p.ingest(Document(doc_id=doc_id, patient_id=patient_id, text=text))
    return p


def test_patient_interaction_flagged_with_both_citations():
    note = (
        "Patient: Test One   MRN: 1112223\n\n"
        "Assessment and Plan: Continue warfarin 5mg daily and aspirin 81mg daily.\n"
    )
    p = _pipeline_with(note)
    flags = p.interactions("PX")
    assert len(flags) == 1
    f = flags[0]
    assert {f["drug_a"], f["drug_b"]} == {"Warfarin", "Aspirin"}
    assert f["severity"] == "major"
    # Provenance from BOTH medications is preserved.
    assert len(f["citations"]) >= 1
    assert all(c.startswith("[note-x#") for c in f["citations"])
    assert "bleeding" in f["description"].lower()


def test_no_interaction_when_only_one_drug():
    note = "Assessment and Plan: Continue metformin 500mg BID.\n"
    p = _pipeline_with(note)
    assert p.interactions("PX") == []


def test_negated_medication_not_flagged():
    note = (
        "Assessment and Plan: Continue warfarin 5mg daily. "
        "Patient is not taking aspirin.\n"
    )
    p = _pipeline_with(note)
    # Aspirin is negated, so the warfarin+aspirin pair must not be flagged.
    assert p.interactions("PX") == []


def test_enrichment_adds_concept_edges():
    note = "Assessment and Plan: Continue warfarin and aspirin.\n"
    p = _pipeline_with(note)
    added = p.kg.enrich_drug_interactions()
    assert added >= 1
    # Idempotent: re-running adds no duplicate edges.
    assert p.kg.enrich_drug_interactions() == 0
    edges = [d for _, _, d in p.kg.g.edges(data=True) if d["rel"] == "INTERACTS_WITH"]
    assert edges and edges[0]["severity"] == "major"


def test_interactions_across_all_patients():
    p = Pipeline()
    p.ingest(Document(doc_id="n1", patient_id="A",
                      text="Plan: warfarin and aspirin.\n"))
    p.ingest(Document(doc_id="n2", patient_id="B",
                      text="Plan: metformin only.\n"))
    flags = p.interactions()  # all patients
    assert len(flags) == 1
    assert flags[0]["patient_id"] == "A"
