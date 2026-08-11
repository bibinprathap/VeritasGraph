"""Document-level assertion reconciliation with contradiction detection.

Mirrors OpenMed ``clinical/assertion_graph.py``:

* Entities are grouped by coded-concept identity.
* Section authority decides the reconciled polarity/axes when evidence
  disagrees (assessment/plan > problem list > HPI > history > social/family).
* When affirmed and negated evidence coexist for the same concept, a
  contradiction is reported (with the conflicting spans) instead of silently
  merging into a clean assertion.

The output is an assistive review artifact, not a clinical decision engine.
"""

from __future__ import annotations

from collections import defaultdict

from .models import (
    AFFIRMED,
    CERTAIN,
    NEGATED,
    RECENT,
    Assertion,
    Entity,
    section_authority,
)

# Temporality precedence when merging (most specific wins for display).
_TEMPORALITY_RANK = {"recent": 2, "historical": 1, "hypothetical": 0}


def reconcile(entities: list[Entity]) -> list[Assertion]:
    """Reconcile per-mention entities into document-level assertions."""
    groups: dict[str, list[Entity]] = defaultdict(list)
    for e in entities:
        if e.concept is None:
            continue
        groups[e.concept.key()].append(e)

    assertions: list[Assertion] = []
    for _, group in groups.items():
        assertions.append(_reconcile_group(group))
    return assertions


def _reconcile_group(group: list[Entity]) -> Assertion:
    # Highest-authority evidence drives the reconciled axes.
    best = max(group, key=lambda e: section_authority(e.span.section))
    best_auth = section_authority(best.span.section)
    top = [e for e in group if section_authority(e.span.section) == best_auth]

    # Reconciled negation: majority among the top-authority evidence.
    neg_votes = sum(1 for e in top if e.context.negation == NEGATED)
    aff_votes = len(top) - neg_votes
    negation = NEGATED if neg_votes > aff_votes else AFFIRMED

    # Contradiction: affirmed and negated evidence coexist anywhere for the concept
    # (only meaningful for the patient as experiencer).
    patient_ev = [e for e in group if e.context.experiencer == "patient"]
    polarities = {e.context.negation for e in patient_ev}
    contradiction = AFFIRMED in polarities and NEGATED in polarities
    conflicting = (
        [e.span for e in patient_ev] if contradiction else []
    )

    certainty = min(
        (e.context.certainty for e in top),
        key=lambda c: 0 if c == "uncertain" else 1,
        default=CERTAIN,
    )
    temporality = max(
        (e.context.temporality for e in top),
        key=lambda t: _TEMPORALITY_RANK.get(t, 0),
        default=RECENT,
    )
    experiencer = best.context.experiencer

    # Merge structured attributes (last non-empty wins per key).
    attributes: dict = {}
    for e in group:
        for k, v in e.attributes.items():
            attributes.setdefault(k, v)

    return Assertion(
        concept=best.concept,
        label=best.label,
        negation=negation,
        certainty=certainty,
        temporality=temporality,
        experiencer=experiencer,
        evidence=[e.span for e in group],
        contradiction=contradiction,
        conflicting_spans=conflicting,
        attributes=attributes,
    )
