"""
VeritasReason — Deterministic reasoning & decision-intelligence layer for VeritasGraph.

This package is a thin re-branding wrapper around the VeritasReason engine. It exposes
the rule-based reasoner, triplet store, and W3C PROV-O provenance under a name
that aligns with the VeritasGraph product family.

Typical use::

    from veritas_reason import TripletStore, ForwardChainer, RuleSet

    ts = TripletStore.connect()
    rules = RuleSet.load("rules/")
    chainer = ForwardChainer(ts, rules)
    derivations = chainer.run()

VeritasGraph (GraphRAG over unstructured text) + VeritasReason (deterministic
reasoning over structured facts) together answer enterprise compliance questions
with full citations.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    "TripletStore",
    "ForwardChainer",
    "RuleSet",
    "Provenance",
]

# Re-export VeritasReason primitives under VeritasReason names. Imports are guarded so
# that downstream code can still import veritas_reason even when the optional
# veritasreason install isn't present (e.g. during docs build).
try:  # pragma: no cover - exercised only when veritasreason is installed
    from veritasreason.triplet_store import TripletStore  # type: ignore
    from veritasreason.reasoning import ForwardChainer, RuleSet  # type: ignore
    from veritasreason.provenance import Provenance  # type: ignore
except Exception:  # pragma: no cover
    TripletStore = None  # type: ignore[assignment]
    ForwardChainer = None  # type: ignore[assignment]
    RuleSet = None  # type: ignore[assignment]
    Provenance = None  # type: ignore[assignment]
