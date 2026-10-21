"""Agent orchestrator (paper §3.1).

Ties the layers together into one governed, observable, zero-trust flow:

    IAM authorize -> (step-up if needed) -> retrieve -> govern -> observe -> answer

Mirrors the ``studio_api`` per-turn pipeline (Guardrails -> Memory -> KG ->
Headroom -> Tools -> Data log).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from .iam import IAMGate, User, Action
from .governance import GovernanceEngine
from .retrieval import RetrievalEngine
from .observability import Observability


class TaskType(str, Enum):
    LITERATURE = "literature"
    TRIALS = "trials"
    ADVERSE_EVENTS = "adverse_events"
    EXPORT = "export"
    UNKNOWN = "unknown"


@dataclass
class AgentResponse:
    answer: str
    approved: bool
    citations: List[str] = field(default_factory=list)
    audit_id: str = ""
    task_type: TaskType = TaskType.UNKNOWN
    reason: str = ""
    escalated: bool = False


# Keyword -> (task, required action) routing table.
_ROUTES = [
    (("adverse", "faers", "safety", "lactic"), TaskType.ADVERSE_EVENTS, Action.QUERY_ADVERSE_EVENTS),
    (("trial", "nct", "sglt2"), TaskType.TRIALS, Action.QUERY_TRIALS),
    (("export", "download", "patient data"), TaskType.EXPORT, Action.EXPORT_PATIENT_DATA),
    (("metformin", "diabetes", "egfr", "therapy", "literature"), TaskType.LITERATURE, Action.QUERY_LITERATURE),
]


class MedTrustAgent:
    def __init__(
        self,
        iam: IAMGate | None = None,
        retrieval: RetrievalEngine | None = None,
        governance: GovernanceEngine | None = None,
        observability: Observability | None = None,
    ) -> None:
        self.iam = iam or IAMGate()
        self.retrieval = retrieval or RetrievalEngine()
        self.governance = governance or GovernanceEngine()
        self.obs = observability or Observability()

    def route(self, query: str) -> tuple[TaskType, Action | None]:
        q = query.lower()
        for keywords, task, action in _ROUTES:
            if any(k in q for k in keywords):
                return task, action
        return TaskType.UNKNOWN, None

    def handle(self, user: User, query: str) -> AgentResponse:
        span = self.obs.start_span("request", user=user.user_id)
        self.obs.incr("requests")

        task, action = self.route(query)
        if action is None:
            self.obs.incr("unsupported")
            self.obs.end_span(span)
            return AgentResponse(
                answer="",
                approved=False,
                task_type=task,
                reason="unsupported task; no matching route",
            )

        decision = self.iam.authorize(user, action)
        if not decision.allowed:
            self.obs.incr("access_blocked")
            if decision.requires_step_up:
                self.obs.incr("step_up_required")
            self.obs.end_span(span)
            return AgentResponse(
                answer="",
                approved=False,
                task_type=task,
                reason=decision.reason,
                escalated=decision.requires_step_up,
            )

        evidence = self.retrieval.retrieve(query)
        answer = " ".join(ev.text for ev in evidence)

        result = self.governance.review(user.user_id, answer, evidence)
        if not result.approved:
            self.obs.incr("governance_blocked")
            self.obs.end_span(span)
            return AgentResponse(
                answer="",
                approved=False,
                task_type=task,
                reason=result.reason,
                audit_id=result.audit_id,
                escalated=True,
            )

        self.obs.incr("answered")
        self.obs.end_span(span)
        return AgentResponse(
            answer=answer,
            approved=True,
            citations=result.citations,
            audit_id=result.audit_id,
            task_type=task,
            reason="ok",
        )
