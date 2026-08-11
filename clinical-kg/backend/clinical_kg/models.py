"""Core data models for the HIPAA-Safe Clinical Knowledge Graph.

All models are plain dataclasses so the pipeline has zero heavy dependencies and
runs fully on-prem. Every clinical fact carries span-level provenance so that
answers are attributable end to end.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# ConText decision axes (mirrors OpenMed openmed.clinical.context)
# ---------------------------------------------------------------------------

Negation = Literal["affirmed", "negated"]
Certainty = Literal["certain", "uncertain"]
Temporality = Literal["recent", "historical", "hypothetical"]
Experiencer = Literal["patient", "other"]

AFFIRMED: Negation = "affirmed"
NEGATED: Negation = "negated"
CERTAIN: Certainty = "certain"
UNCERTAIN: Certainty = "uncertain"
RECENT: Temporality = "recent"
HISTORICAL: Temporality = "historical"
HYPOTHETICAL: Temporality = "hypothetical"
PATIENT: Experiencer = "patient"
OTHER: Experiencer = "other"

EntityLabel = Literal["CONDITION", "MEDICATION", "LAB", "PROCEDURE"]

# Section authority: higher number wins during reconciliation.
SECTION_AUTHORITY: dict[str, int] = {
    "assessment_and_plan": 5,
    "assessment": 5,
    "plan": 5,
    "problem_list": 4,
    "hpi": 3,
    "history_of_present_illness": 3,
    "past_medical_history": 2,
    "pmh": 2,
    "history": 2,
    "social_history": 1,
    "family_history": 1,
    "": 0,
}


def section_authority(section: str) -> int:
    """Return the reconciliation authority for a (normalized) section name."""
    return SECTION_AUTHORITY.get((section or "").strip().lower(), 0)


@dataclass(frozen=True)
class Concept:
    """A coded clinical concept (ICD-10-CM, RxNorm, SNOMED CT, LOINC)."""

    system: str  # "SNOMED" | "ICD10" | "RxNorm" | "LOINC"
    code: str
    display: str

    def key(self) -> str:
        return f"{self.system}:{self.code}"


@dataclass
class Span:
    """Provenance: exactly where a fact was found."""

    doc_id: str
    chunk_id: int
    section: str
    start: int
    end: int
    text: str

    def citation(self) -> str:
        """The ``[doc#chunk]`` citation string used throughout VeritasGraph."""
        return f"[{self.doc_id}#{self.chunk_id}]"


@dataclass
class ContextAxes:
    negation: Negation = AFFIRMED
    certainty: Certainty = CERTAIN
    temporality: Temporality = RECENT
    experiencer: Experiencer = PATIENT


@dataclass
class Entity:
    """A single mention extracted from text with its context axes."""

    text: str
    label: EntityLabel
    span: Span
    context: ContextAxes = field(default_factory=ContextAxes)
    concept: Optional[Concept] = None
    # Structured detail for medications / labs.
    attributes: dict = field(default_factory=dict)


@dataclass
class Assertion:
    """A reconciled, document-level clinical assertion for one concept."""

    concept: Concept
    label: EntityLabel
    negation: Negation
    certainty: Certainty
    temporality: Temporality
    experiencer: Experiencer
    evidence: list[Span] = field(default_factory=list)
    contradiction: bool = False
    conflicting_spans: list[Span] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)


@dataclass
class Document:
    """A raw clinical document to ingest."""

    doc_id: str
    patient_id: str
    text: str
    encounter_date: Optional[str] = None  # ISO-8601
    encounter_type: str = "note"


@dataclass
class DeidResult:
    text: str
    replacements: int
    vault_id: str


@dataclass
class PatientMatch:
    patient_id: str
    reasons: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
