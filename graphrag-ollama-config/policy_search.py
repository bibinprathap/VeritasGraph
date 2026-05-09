"""
Policy-compliance search orchestrator.

Combines:
  * VeritasGraph (GraphRAG) — finds the policy text and clause that the user's
    natural-language question refers to.
  * VeritasReason — fires the corresponding rules over the structured triples
    and returns the deterministic list of violators with full provenance.

The result is a structured payload the Gradio UI in app.py can render either
as a table (violators) or as LLM-narrated prose with citations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from veritas_reason import TripletStore, ForwardChainer, RuleSet
except Exception:  # pragma: no cover
    TripletStore = ForwardChainer = RuleSet = None  # type: ignore[assignment]


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RULES_DIR = SCRIPT_DIR.parent / "rules"


@dataclass
class ComplianceResult:
    question: str
    policy_id: str
    rules_fired: list[str]
    violators: list[dict]
    citations: list[dict]
    rag_context: str = ""
    narration: str = ""

    def to_markdown(self) -> str:
        if not self.violators:
            return (
                f"**No violations found** for `{self.policy_id}`.\n\n"
                f"_Rules evaluated:_ {', '.join(self.rules_fired) or '(none)'}"
            )
        lines = [
            f"### Violations of `{self.policy_id}`",
            "",
            "| Subject | Rule | Evidence |",
            "|---|---|---|",
        ]
        for v in self.violators:
            lines.append(
                f"| {v.get('subject','?')} | {v.get('rule','?')} | "
                f"{v.get('evidence','')} |"
            )
        lines.append("")
        lines.append("**Citations**")
        for c in self.citations:
            lines.append(f"- {c.get('policy_doc','?')} — {c.get('clause','')}")
        if self.narration:
            lines.append("")
            lines.append(self.narration)
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 1. Pick the policy the user is asking about (RAG step)
# --------------------------------------------------------------------------- #
async def _identify_policy(question: str, rag_search_fn=None) -> tuple[str, str]:
    """Return (policy_id, rag_context_text).

    Uses VeritasGraph's existing search functions when available; falls back to
    a keyword heuristic so this module is testable in isolation.
    """
    rag_context = ""
    if rag_search_fn is not None:
        try:
            rag_context = await rag_search_fn(question)
        except Exception as exc:  # pragma: no cover - UI-side surface
            rag_context = f"(rag unavailable: {exc})"

    q = question.lower()
    if "segregation" in q or "sod" in q or "purchase" in q or "procurement" in q:
        return "policy:SoD", rag_context
    if "leave" in q or "absence" in q or "attendance" in q:
        return "policy:LeavePolicy", rag_context
    if "expense" in q or "reimbursement" in q:
        return "policy:Expense", rag_context
    return "policy:Unknown", rag_context


# --------------------------------------------------------------------------- #
# 2. Run the deterministic reasoner
# --------------------------------------------------------------------------- #
def _run_reasoner(
    policy_id: str,
    rules_dir: Path,
    triplet_store: Any | None = None,
) -> tuple[list[str], list[dict], list[dict]]:
    if ForwardChainer is None or RuleSet is None:
        raise RuntimeError(
            "veritas_reason is not installed. Run: "
            "pip install -e ./veritas-reason"
        )
    if triplet_store is None:
        triplet_store = TripletStore.connect()  # type: ignore[union-attr]

    rules = RuleSet.load(str(rules_dir))
    chainer = ForwardChainer(triplet_store, rules)
    run = chainer.run(filter_tag=policy_id)

    rules_fired = list(getattr(run, "fired_rule_ids", []))
    violators: list[dict] = []
    citations: list[dict] = []

    # The exact API may vary across VeritasReason versions; we defensively support
    # either a `derivations` attribute or a SPARQL fallback.
    for fact in getattr(run, "derivations", []):
        s, p, o = getattr(fact, "spo", (None, None, None))
        if p == "proc:violates" or p == "hr:violates":
            violators.append({
                "subject": s,
                "rule": o,
                "evidence": getattr(fact, "evidence_summary", ""),
            })
        for cite in getattr(fact, "citations", []):
            if cite not in citations:
                citations.append(cite)

    return rules_fired, violators, citations


# --------------------------------------------------------------------------- #
# 3. Public entry point used by app.py
# --------------------------------------------------------------------------- #
async def policy_compliance_search(
    question: str,
    rules_dir: str | os.PathLike | None = None,
    rag_search_fn=None,
    triplet_store: Any | None = None,
    narrator=None,
) -> ComplianceResult:
    """Answer a natural-language compliance question.

    Parameters
    ----------
    question:
        Free-text user question, e.g. "Which purchase orders violate SoD?"
    rules_dir:
        Directory containing YAML rule files. Defaults to ``<repo>/rules``.
    rag_search_fn:
        Async callable ``(question) -> str`` that returns the RAG context for
        policy identification. Pass ``reasoning_local_search`` from app.py.
    triplet_store:
        Optional pre-connected VeritasReason TripletStore.
    narrator:
        Optional async callable ``(result) -> str`` that turns the structured
        payload into prose using the configured LLM.
    """
    rules_dir = Path(rules_dir) if rules_dir else DEFAULT_RULES_DIR

    policy_id, rag_ctx = await _identify_policy(question, rag_search_fn)
    rules_fired, violators, citations = _run_reasoner(
        policy_id, rules_dir, triplet_store
    )

    result = ComplianceResult(
        question=question,
        policy_id=policy_id,
        rules_fired=rules_fired,
        violators=violators,
        citations=citations,
        rag_context=rag_ctx,
    )

    if narrator is not None:
        try:
            result.narration = await narrator(result)
        except Exception as exc:  # pragma: no cover
            result.narration = f"(narration failed: {exc})"

    return result
