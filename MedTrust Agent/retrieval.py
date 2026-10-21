"""Retrieval + grounding layer (paper §3.2).

Reference stub for literature RAG + structured DB grounding + clinical KG. In
production these delegate to ``studio_api.graphrag_engine``, ``clinical-kg``, and
``medkg-signal-reference``. Here we use a small deterministic corpus so answers are
reproducible offline and every returned fact carries a ``[doc#chunk]`` citation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Evidence:
    text: str
    doc_id: str
    chunk: int

    @property
    def citation(self) -> str:
        return f"[{self.doc_id}#{self.chunk}]"


# Deterministic reference corpus (stands in for the graph-grounded engine).
_CORPUS: List[Evidence] = [
    Evidence("Metformin is first-line therapy for type 2 diabetes mellitus.", "pubmed_001", 0),
    Evidence("eGFR below 30 mL/min/1.73m2 contraindicates metformin.", "pubmed_002", 1),
    Evidence("Trial NCT01234567 studied SGLT2 inhibitors in T2DM patients.", "trials_010", 0),
    Evidence("Adverse event report: lactic acidosis associated with metformin overdose.", "faers_077", 3),
    Evidence("Patient P001 has T2DM, on metformin, most recent eGFR 24.", "clinical_kg", 5),
]


class RetrievalEngine:
    """Keyword-overlap retrieval over a fixed corpus (deterministic, offline)."""

    def __init__(self, corpus: List[Evidence] | None = None) -> None:
        self._corpus = corpus if corpus is not None else list(_CORPUS)

    def retrieve(self, query: str, k: int = 3) -> List[Evidence]:
        terms = {t for t in _tokenize(query)}
        scored = []
        for ev in self._corpus:
            overlap = len(terms & set(_tokenize(ev.text)))
            if overlap > 0:
                scored.append((overlap, ev))
        scored.sort(key=lambda x: (-x[0], x[1].doc_id, x[1].chunk))
        return [ev for _, ev in scored[:k]]


def _tokenize(text: str) -> List[str]:
    return [w.strip(".,()").lower() for w in text.split() if len(w) > 2]
