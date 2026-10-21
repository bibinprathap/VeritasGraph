"""MedTrust Agent — reference integration layer.

A dependency-light (stdlib-only) reference implementation of the architecture in
``proposed_research_paper.md``. Each module maps to an existing VeritasGraph folder
(see ``development_plan.md``). This layer is deterministic so the paper's experiments
and tests run offline with no model downloads.
"""

from .iam import IAMGate, AccessDecision, User, Action
from .governance import GovernanceEngine, GovernanceResult, AuditLog
from .retrieval import RetrievalEngine, Evidence
from .observability import Observability, Span
from .agent import MedTrustAgent, AgentResponse, TaskType

__all__ = [
    "IAMGate",
    "AccessDecision",
    "User",
    "Action",
    "GovernanceEngine",
    "GovernanceResult",
    "AuditLog",
    "RetrievalEngine",
    "Evidence",
    "Observability",
    "Span",
    "MedTrustAgent",
    "AgentResponse",
    "TaskType",
]
