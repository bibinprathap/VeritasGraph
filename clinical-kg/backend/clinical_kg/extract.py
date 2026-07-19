"""Clinical entity extraction: section segmentation + dictionary NER.

Produces :class:`Entity` objects with span-level provenance, coded concepts, and
ConText axes. Lab values and medication sigs are parsed into structured
attributes. This mirrors the role of OpenMed's clinical NER + ``sig_parser`` /
``lab_values`` with a deterministic, offline implementation.
"""

from __future__ import annotations

import re

from . import normalize
from .context import classify
from .models import Entity, Span

# Recognized section headers -> normalized section key.
_SECTION_ALIASES: dict[str, str] = {
    "hpi": "hpi",
    "history of present illness": "hpi",
    "problem list": "problem_list",
    "problems": "problem_list",
    "assessment and plan": "assessment_and_plan",
    "assessment & plan": "assessment_and_plan",
    "a/p": "assessment_and_plan",
    "assessment": "assessment",
    "plan": "plan",
    "past medical history": "past_medical_history",
    "pmh": "past_medical_history",
    "medications": "medications",
    "meds": "medications",
    "social history": "social_history",
    "family history": "family_history",
    "labs": "labs",
    "laboratory": "labs",
    "results": "labs",
}

_SECTION_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(h) for h in sorted(_SECTION_ALIASES, key=len, reverse=True)) + r")\s*:",
    re.IGNORECASE | re.MULTILINE,
)

# Chunk = one line; chunk_id is the 0-based line index within the document.


def _sections(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, normalized_section) regions covering the whole text."""
    marks: list[tuple[int, str]] = []
    for m in _SECTION_RE.finditer(text):
        key = _SECTION_ALIASES[m.group(1).strip().lower()]
        marks.append((m.start(), key))
    if not marks or marks[0][0] > 0:
        marks.insert(0, (0, ""))

    regions: list[tuple[int, int, str]] = []
    for i, (pos, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        regions.append((pos, end, key))
    return regions


def _section_at(regions: list[tuple[int, int, str]], pos: int) -> str:
    for start, end, key in regions:
        if start <= pos < end:
            return key
    return ""


def _chunk_id(text: str, pos: int) -> int:
    return text.count("\n", 0, pos)


def _term_pattern(terms: list[str]) -> re.Pattern[str]:
    alt = "|".join(re.escape(t) for t in terms)
    return re.compile(rf"(?<!\w)(?:{alt})(?!\w)", re.IGNORECASE)


_COND_RE = _term_pattern(normalize.all_condition_terms())
_MED_RE = _term_pattern(normalize.all_medication_terms())
_LAB_RE = _term_pattern(normalize.all_lab_terms())
_PROC_RE = _term_pattern(normalize.all_procedure_terms())

# medication sig, e.g. "metformin 500 mg BID", "500mg po bid prn"
_DOSE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|units?|iu)\b", re.I)
_FREQ_RE = re.compile(r"\b(qd|bid|tid|qid|qhs|q\d+h|daily|once daily|twice daily|prn|weekly)\b", re.I)
_ROUTE_RE = re.compile(r"\b(po|iv|im|sc|subq|sublingual|topical|inhaled)\b", re.I)

# lab value, e.g. "eGFR 24", "HbA1c 7.8%", "eGFR of 24 mL/min"
_VALUE_RE = re.compile(r"(?:of\s+|=\s*|:\s*|is\s+)?(\d+(?:\.\d+)?)\s*(%|mg/dl|mmol/l|ml/min[^\s.,;]*)?", re.I)


def _make_entity(text: str, m: re.Match, label: str, section: str, concept, icd10=None, attrs=None) -> Entity:
    start, end = m.span()
    span = Span(
        doc_id="",  # filled by pipeline
        chunk_id=_chunk_id(text, start),
        section=section,
        start=start,
        end=end,
        text=m.group(0),
    )
    ctx = classify(text, start, end, section)
    entity = Entity(
        text=m.group(0), label=label, span=span, context=ctx, concept=concept,
        attributes=attrs or {},
    )
    if icd10:
        entity.attributes["icd10"] = icd10
    return entity


def extract(text: str, doc_id: str) -> list[Entity]:
    """Extract clinical entities from a single document's text."""
    regions = _sections(text)
    entities: list[Entity] = []

    for m in _COND_RE.finditer(text):
        section = _section_at(regions, m.start())
        concept, icd10 = normalize.normalize_condition(m.group(0))
        if concept is None:
            continue
        entities.append(_make_entity(text, m, "CONDITION", section, concept, icd10))

    for m in _MED_RE.finditer(text):
        section = _section_at(regions, m.start())
        concept = normalize.normalize_medication(m.group(0))
        if concept is None:
            continue
        tail = text[m.end(): m.end() + 40]
        attrs: dict = {}
        if (dm := _DOSE_RE.search(tail)):
            attrs["dose"] = f"{dm.group(1)} {dm.group(2).lower()}"
        if (fm := _FREQ_RE.search(tail)):
            attrs["frequency"] = fm.group(1).lower()
        if (rm := _ROUTE_RE.search(tail)):
            attrs["route"] = rm.group(1).lower()
        entities.append(_make_entity(text, m, "MEDICATION", section, concept, attrs=attrs))

    for m in _LAB_RE.finditer(text):
        section = _section_at(regions, m.start())
        concept = normalize.normalize_lab(m.group(0))
        if concept is None:
            continue
        tail = text[m.end(): m.end() + 30]
        attrs = {}
        if (vm := _VALUE_RE.search(tail)) and vm.group(1):
            attrs["value"] = float(vm.group(1))
            if vm.group(2):
                attrs["unit"] = vm.group(2)
        entities.append(_make_entity(text, m, "LAB", section, concept, attrs=attrs))

    for m in _PROC_RE.finditer(text):
        section = _section_at(regions, m.start())
        concept = normalize.normalize_procedure(m.group(0))
        if concept is None:
            continue
        entities.append(_make_entity(text, m, "PROCEDURE", section, concept))

    # Assign the document id to every provenance span.
    for e in entities:
        e.span.doc_id = doc_id
    return entities
