"""Query parsing + multi-hop cohort execution + pipeline tests."""

from __future__ import annotations

from clinical_kg import query
from clinical_kg.pipeline import Pipeline
from clinical_kg.sample_data import SAMPLE_DOCUMENTS


def test_parse_query_extracts_all_parts():
    q = query.parse_query("patients with T2DM taking metformin whose most recent eGFR < 30")
    assert "SNOMED:44054006" in q.conditions
    assert "RxNorm:6809" in q.medications
    assert len(q.lab_filters) == 1
    lf = q.lab_filters[0]
    assert lf.concept_key == "LOINC:33914-3"
    assert lf.op == "<"
    assert lf.value == 30.0


def test_flagship_cohort_query():
    pipe = Pipeline()
    pipe.ingest_all(SAMPLE_DOCUMENTS)
    matches = pipe.query("List patients with T2DM taking metformin whose most recent eGFR < 30")
    ids = {m.patient_id for m in matches}
    # P001 (eGFR 24) and P004 (eGFR 22) qualify; P002 eGFR 68 excluded;
    # P003 has no diabetes.
    assert ids == {"P001", "P004"}


def test_matches_include_citations():
    pipe = Pipeline()
    pipe.ingest_all(SAMPLE_DOCUMENTS)
    matches = pipe.query("patients with T2DM taking metformin whose eGFR < 30")
    assert all(m.citations for m in matches)
    assert all(m.reasons for m in matches)


def test_negated_condition_excluded():
    pipe = Pipeline()
    pipe.ingest_all(SAMPLE_DOCUMENTS)
    # P003 explicitly has "no evidence of diabetes".
    matches = pipe.query("patients with diabetes")
    ids = {m.patient_id for m in matches}
    assert "P003" not in ids


def test_pipeline_deidentifies_on_ingest():
    pipe = Pipeline()
    result = pipe.ingest(SAMPLE_DOCUMENTS[0])
    assert result.replacements > 0


def test_pipeline_detects_contradiction():
    pipe = Pipeline()
    result = pipe.ingest(SAMPLE_DOCUMENTS[0])  # note-001 has HPI-denies vs problem-list T2DM
    codes = {c.concept.code for c in result.contradictions}
    assert "44054006" in codes


def test_stats_populated():
    pipe = Pipeline()
    pipe.ingest_all(SAMPLE_DOCUMENTS)
    stats = pipe.stats()
    assert stats["nodes"] > 0
    assert "Patient" in stats["by_type"]
    assert stats["by_type"]["Patient"] == 4
