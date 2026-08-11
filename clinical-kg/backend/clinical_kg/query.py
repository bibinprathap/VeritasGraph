"""Multi-hop cohort queries over the knowledge graph.

Supports the flagship query from the use case:

    "List patients with T2DM taking metformin whose most recent eGFR < 30"

A structured :class:`CohortQuery` drives graph traversal; :func:`parse_query`
turns free text into that structure using the clinical vocabulary plus a small
lab-threshold grammar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import normalize
from .graph import KnowledgeGraph
from .models import NEGATED, PatientMatch

_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "=": lambda a, b: a == b,
    "==": lambda a, b: a == b,
}


@dataclass
class LabFilter:
    concept_key: str  # e.g. "LOINC:33914-3"
    display: str
    op: str
    value: float
    aggregate: str = "latest"  # latest | any | min | max


@dataclass
class CohortQuery:
    conditions: list[str] = field(default_factory=list)   # concept keys
    medications: list[str] = field(default_factory=list)  # concept keys
    procedures: list[str] = field(default_factory=list)
    lab_filters: list[LabFilter] = field(default_factory=list)
    include_negated: bool = False


_LAB_THRESHOLD_RE = re.compile(
    r"(" + "|".join(re.escape(t) for t in normalize.all_lab_terms()) + r")"
    r"[^<>=\d]{0,20}?(<=|>=|<|>|=)\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def parse_query(text: str) -> CohortQuery:
    """Parse a natural-language cohort request into a structured query."""
    q = CohortQuery()
    low = text.lower()

    # Lab thresholds first, then strip so lab words don't match as conditions.
    consumed = text
    for m in _LAB_THRESHOLD_RE.finditer(text):
        concept = normalize.normalize_lab(m.group(1))
        if concept:
            q.lab_filters.append(
                LabFilter(concept.key(), concept.display, m.group(2), float(m.group(3)))
            )
        consumed = consumed.replace(m.group(0), " ")
    low_consumed = consumed.lower()

    for term in normalize.all_condition_terms():
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", low_consumed):
            concept, _ = normalize.normalize_condition(term)
            if concept and concept.key() not in q.conditions:
                q.conditions.append(concept.key())
    for term in normalize.all_medication_terms():
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", low_consumed):
            concept = normalize.normalize_medication(term)
            if concept and concept.key() not in q.medications:
                q.medications.append(concept.key())
    for term in normalize.all_procedure_terms():
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", low_consumed):
            concept = normalize.normalize_procedure(term)
            if concept and concept.key() not in q.procedures:
                q.procedures.append(concept.key())

    if "including negated" in low or "even if denied" in low:
        q.include_negated = True
    return q


def _patient_ids(kg: KnowledgeGraph) -> list[str]:
    return [d["patient_id"] for _, d in kg.g.nodes(data=True) if d["ntype"] == "Patient"]


def _fact(kg: KnowledgeGraph, patient_id: str, concept_key: str) -> dict | None:
    node_id = f"{concept_key}@{patient_id}"
    if node_id in kg.g:
        return {**kg.g.nodes[node_id], "node_id": node_id}
    return None


def _citations(kg: KnowledgeGraph, node_id: str) -> list[str]:
    return sorted(
        {
            kg.g.nodes[s]["citation"]
            for _, s, ed in kg.g.out_edges(node_id, data=True)
            if kg.g.nodes[s]["ntype"] == "Span" and ed["rel"] == "EVIDENCED_BY"
        }
    )


def run(kg: KnowledgeGraph, query: CohortQuery) -> list[PatientMatch]:
    """Execute a structured cohort query, returning matches with citations."""
    matches: list[PatientMatch] = []
    for pid in _patient_ids(kg):
        reasons: list[str] = []
        citations: list[str] = []
        ok = True

        for ckey in query.conditions:
            fact = _fact(kg, pid, ckey)
            if not fact or (fact["negation"] == NEGATED and not query.include_negated):
                ok = False
                break
            reasons.append(f"has condition {fact['display']}")
            citations += _citations(kg, fact["node_id"])
        if not ok:
            continue

        for mkey in query.medications:
            fact = _fact(kg, pid, mkey)
            if not fact or (fact["negation"] == NEGATED and not query.include_negated):
                ok = False
                break
            reasons.append(f"takes {fact['display']}")
            citations += _citations(kg, fact["node_id"])
        if not ok:
            continue

        for pkey in query.procedures:
            fact = _fact(kg, pid, pkey)
            if not fact:
                ok = False
                break
            reasons.append(f"had {fact['display']}")
            citations += _citations(kg, fact["node_id"])
        if not ok:
            continue

        for lf in query.lab_filters:
            fact = _fact(kg, pid, lf.concept_key)
            if not fact or "value" not in fact:
                ok = False
                break
            if not _OPS[lf.op](float(fact["value"]), lf.value):
                ok = False
                break
            reasons.append(f"{lf.display} {fact['value']} {lf.op} {lf.value}")
            citations += _citations(kg, fact["node_id"])
        if not ok:
            continue

        matches.append(PatientMatch(patient_id=pid, reasons=reasons, citations=sorted(set(citations))))
    return matches
