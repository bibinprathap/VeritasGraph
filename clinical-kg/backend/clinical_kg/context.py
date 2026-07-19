"""Deterministic ConText axes: negation, certainty, temporality, experiencer.

Ported NegEx/ConText-style cue matching, mirroring OpenMed
``openmed.clinical.context``. Given a target span and the surrounding sentence
window, classify the four assertion axes used during reconciliation.
"""

from __future__ import annotations

import re

from .models import (
    AFFIRMED,
    CERTAIN,
    HISTORICAL,
    HYPOTHETICAL,
    NEGATED,
    OTHER,
    PATIENT,
    RECENT,
    UNCERTAIN,
    ContextAxes,
)

# Pseudo-negations are masked before real negation cues are counted so that
# "no evidence of" is not double-counted and "no change" does not negate.
PSEUDO_NEGATION_CUES = [
    "no change", "no increase", "no decrease", "not necessarily", "no further",
    "not only", "no significant change",
]

NEGATION_CUES = [
    "no evidence of", "no signs of", "without evidence of", "denies any",
    "denies", "denied", "negative for", "rules out", "ruled out", "without",
    "absence of", "no", "not", "free of", "resolved", "ruled-out",
]

HISTORICAL_CUES = [
    "history of", "h/o", "hx of", "hx", "past medical history", "pmh",
    "previous", "previously", "prior", "s/p", "status post", "in the past",
    "resolved", "old", "chronic",
]

HYPOTHETICAL_CUES = [
    "if", "should", "in case of", "as needed", "prn", "possible", "possibly",
    "rule out", "r/o", "versus", "vs", "to evaluate for", "concern for",
    "risk of", "prophylaxis",
]

UNCERTAINTY_CUES = [
    "possible", "possibly", "probable", "probably", "likely", "unlikely",
    "suspected", "suspicious for", "cannot exclude", "cannot rule out",
    "questionable", "may", "might", "concern for", "differential", "r/o",
    "rule out",
]

EXPERIENCER_CUES = [
    "father", "mother", "brother", "sister", "family history", "fhx",
    "family hx", "parent", "sibling", "grandmother", "grandfather", "uncle",
    "aunt", "cousin", "son", "daughter",
]


def _compile(cues: list[str]) -> re.Pattern[str]:
    alt = "|".join(
        r"\s+".join(re.escape(p) for p in cue.split())
        for cue in sorted(set(cues), key=len, reverse=True)
    )
    return re.compile(rf"(?<!\w)(?:{alt})(?!\w)", re.IGNORECASE)


_NEG = _compile(NEGATION_CUES)
_PSEUDO = _compile(PSEUDO_NEGATION_CUES)
_HIST = _compile(HISTORICAL_CUES)
_HYPO = _compile(HYPOTHETICAL_CUES)
_UNC = _compile(UNCERTAINTY_CUES)
_EXP = _compile(EXPERIENCER_CUES)


def _window(text: str, start: int, end: int, left: int = 60, right: int = 20) -> tuple[str, str]:
    """Return (pre-context, post-context) around a target span, clipped to the sentence."""
    sent_start = max(
        text.rfind(".", 0, start),
        text.rfind(";", 0, start),
        text.rfind("\n", 0, start),
    )
    sent_start = sent_start + 1 if sent_start != -1 else 0
    sent_start = max(sent_start, start - left)

    nxt = [p for p in (text.find(".", end), text.find("\n", end)) if p != -1]
    sent_end = min(nxt) if nxt else len(text)
    sent_end = min(sent_end, end + right)

    return text[sent_start:start], text[end:sent_end]


def classify(text: str, start: int, end: int, section: str = "") -> ContextAxes:
    """Classify the four ConText axes for a target span within ``text``."""
    pre, post = _window(text, start, end)
    scope = f"{pre} {post}"
    section_l = (section or "").strip().lower()

    # Negation: mask pseudo-negations first, then look in the pre-context.
    pre_masked = _PSEUDO.sub(" ", pre)
    negation = NEGATED if _NEG.search(pre_masked) else AFFIRMED

    # Temporality.
    if _HYPO.search(scope):
        temporality = HYPOTHETICAL
    elif _HIST.search(scope) or "history" in section_l:
        temporality = HISTORICAL
    else:
        temporality = RECENT

    # Certainty.
    certainty = UNCERTAIN if _UNC.search(scope) else CERTAIN

    # Experiencer.
    experiencer = (
        OTHER
        if _EXP.search(scope) or "family" in section_l
        else PATIENT
    )

    return ContextAxes(
        negation=negation,
        certainty=certainty,
        temporality=temporality,
        experiencer=experiencer,
    )
