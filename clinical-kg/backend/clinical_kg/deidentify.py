"""Safe Harbor de-identification (HIPAA 18 identifiers).

On-device, regex-driven PHI removal with a sealed surrogate vault so text can be
re-identified later under audit. This is deterministic and dependency-free.

For production use, wire in OpenMed's model-backed ``deidentify`` via
:mod:`clinical_kg.openmed_adapter`; the interface is identical.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from .models import DeidResult

# ---------------------------------------------------------------------------
# Safe Harbor patterns. Order matters: longer / more specific first.
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("URL", re.compile(r"\bhttps?://[^\s]+\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(\d{3}\)[\s.-]?|\d{3}[\s.-])\d{3}[\s.-]?\d{4}(?!\d)"
        ),
    ),
    ("MRN", re.compile(r"\b(?:MRN|Medical Record(?: Number)?)[:#\s]*([A-Z0-9]{5,})\b", re.I)),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    (
        "DATE",
        re.compile(
            r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
            r"|\d{4}-\d{2}-\d{2}"
            r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
            re.I,
        ),
    ),
    ("ZIP", re.compile(r"\b\d{5}(?:-\d{4})?\b")),
    # Ages over 89 must be removed under Safe Harbor.
    ("AGE>89", re.compile(r"\b(9\d|1\d\d)\s*(?:years?[- ]old|yo|y/o|years? of age)\b", re.I)),
    # Names following common honorifics / labels.
    (
        "NAME",
        re.compile(
            r"\b(?:Mr|Mrs|Ms|Dr|Miss|Patient|Pt|Name)\.?:?\s+"
            r"([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+)",
        ),
    ),
]


@dataclass
class SurrogateVault:
    """In-memory sealed store mapping surrogate tokens to original PHI.

    A real deployment would encrypt entries at rest (OpenMed provides
    ``SurrogateVault`` with an encryption scheme). Here we keep the same API.
    """

    _store: dict[str, dict[str, str]] = field(default_factory=dict)

    def seal(self, mapping: dict[str, str]) -> str:
        vault_id = uuid.uuid4().hex
        self._store[vault_id] = mapping
        return vault_id

    def reveal(self, vault_id: str) -> dict[str, str]:
        return self._store.get(vault_id, {})


def _iter_matches(text: str):
    """Yield non-overlapping (category, start, end, value) spans, longest-first."""
    claimed: list[tuple[int, int]] = []

    def overlaps(s: int, e: int) -> bool:
        return any(not (e <= cs or s >= ce) for cs, ce in claimed)

    for category, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            # Prefer the capturing group (the actual PHI) when present.
            if m.groups():
                s, e = m.span(1)
            else:
                s, e = m.span(0)
            if overlaps(s, e):
                continue
            claimed.append((s, e))
            yield category, s, e, text[s:e]


def deidentify(
    text: str,
    vault: SurrogateVault | None = None,
) -> DeidResult:
    """Replace PHI with typed surrogate tokens and seal originals in the vault."""
    vault = vault or SurrogateVault()
    matches = sorted(_iter_matches(text), key=lambda t: t[1])

    mapping: dict[str, str] = {}
    counters: dict[str, int] = {}
    out: list[str] = []
    cursor = 0
    for category, start, end, value in matches:
        out.append(text[cursor:start])
        counters[category] = counters.get(category, 0) + 1
        token = f"[{category}_{counters[category]}]"
        mapping[token] = value
        out.append(token)
        cursor = end
    out.append(text[cursor:])

    vault_id = vault.seal(mapping)
    return DeidResult(text="".join(out), replacements=len(mapping), vault_id=vault_id)


def reidentify(text: str, vault: SurrogateVault, vault_id: str) -> str:
    """Restore original PHI from the sealed vault (audited operation)."""
    mapping = vault.reveal(vault_id)
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text
