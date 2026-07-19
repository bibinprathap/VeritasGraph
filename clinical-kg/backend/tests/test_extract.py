"""Extraction + ConText axis tests."""

from __future__ import annotations

from clinical_kg import context, extract


def _find(entities, display):
    return [e for e in entities if e.concept and e.concept.display == display]


def test_extracts_condition_med_lab():
    text = """Problem List:
1. Type 2 diabetes mellitus, on metformin 500mg BID.
Labs: eGFR 24 mL/min.
"""
    ents = extract.extract(text, "doc-x")
    labels = {e.label for e in ents}
    assert {"CONDITION", "MEDICATION", "LAB"} <= labels
    assert _find(ents, "Type 2 diabetes mellitus")
    assert _find(ents, "Metformin")
    assert _find(ents, "Estimated glomerular filtration rate")


def test_medication_sig_parsed():
    ents = extract.extract("metformin 500mg BID po", "d")
    med = _find(ents, "Metformin")[0]
    assert med.attributes.get("dose") == "500 mg"
    assert med.attributes.get("frequency") == "bid"
    assert med.attributes.get("route") == "po"


def test_lab_value_parsed():
    ents = extract.extract("Labs: eGFR 24 mL/min", "d")
    lab = [e for e in ents if e.concept and e.concept.code == "33914-3"][0]
    assert lab.attributes.get("value") == 24.0


def test_negation_in_hpi():
    text = "HPI: Patient denies any history of diabetes."
    ents = extract.extract(text, "d")
    dm = [e for e in ents if e.concept and e.concept.code == "44054006"][0]
    assert dm.context.negation == "negated"


def test_family_history_is_other_experiencer():
    text = "Family History: Father with myocardial infarction."
    ents = extract.extract(text, "d")
    mi = [e for e in ents if e.concept and e.concept.code == "22298006"][0]
    assert mi.context.experiencer == "other"


def test_context_uncertainty_and_hypothetical():
    axes = context.classify("possible pneumonia", 9, 18)
    assert axes.certainty == "uncertain"
    hypo = context.classify("rule out sepsis", 9, 15)
    assert hypo.temporality == "hypothetical"


def test_pseudo_negation_not_negated():
    # "no change in" should not negate the finding.
    text = "no change in hypertension"
    ents = extract.extract(text, "d")
    htn = [e for e in ents if e.concept and e.concept.code == "38341003"][0]
    assert htn.context.negation == "affirmed"
