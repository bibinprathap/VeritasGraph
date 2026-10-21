"""Zero-Trust / IAM layer (paper §3.3).

Least-privilege authorization with step-up for high-risk actions. Models the
air-gapped, zero-egress posture of ``veritasgraph_mcp``: every request is explicitly
authorized against a role->permission matrix; sensitive data actions require an
approved step-up token.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Set


class Action(str, Enum):
    """Actions a caller may attempt. High-risk actions require step-up."""

    QUERY_LITERATURE = "query_literature"
    QUERY_TRIALS = "query_trials"
    QUERY_ADVERSE_EVENTS = "query_adverse_events"
    EXPORT_PATIENT_DATA = "export_patient_data"
    CLEAR_GRAPH = "clear_graph"


HIGH_RISK: Set[Action] = {Action.EXPORT_PATIENT_DATA, Action.CLEAR_GRAPH}


@dataclass(frozen=True)
class User:
    user_id: str
    role: str
    team: str = "default"


@dataclass
class AccessDecision:
    allowed: bool
    reason: str
    requires_step_up: bool = False


# Least-privilege role -> permitted actions matrix.
_ROLE_PERMISSIONS: Dict[str, Set[Action]] = {
    "clinician": {
        Action.QUERY_LITERATURE,
        Action.QUERY_TRIALS,
        Action.QUERY_ADVERSE_EVENTS,
    },
    "safety_analyst": {
        Action.QUERY_LITERATURE,
        Action.QUERY_TRIALS,
        Action.QUERY_ADVERSE_EVENTS,
        Action.EXPORT_PATIENT_DATA,
    },
    "medical_affairs": {
        Action.QUERY_LITERATURE,
        Action.QUERY_TRIALS,
    },
    "admin": set(Action),
    "guest": {Action.QUERY_LITERATURE},
}


class IAMGate:
    """Evaluates access using least privilege plus step-up for high-risk actions."""

    def __init__(self) -> None:
        self._granted_step_up: Set[str] = set()

    def grant_step_up(self, user: User, action: Action) -> None:
        """Record an approved step-up authorization (e.g. human approval)."""
        self._granted_step_up.add(self._key(user, action))

    def authorize(self, user: User, action: Action) -> AccessDecision:
        permitted = _ROLE_PERMISSIONS.get(user.role, set())
        if action not in permitted:
            return AccessDecision(
                allowed=False,
                reason=f"role '{user.role}' lacks permission for '{action.value}'",
            )
        if action in HIGH_RISK and self._key(user, action) not in self._granted_step_up:
            return AccessDecision(
                allowed=False,
                reason=f"high-risk action '{action.value}' requires step-up authorization",
                requires_step_up=True,
            )
        return AccessDecision(allowed=True, reason="authorized")

    @staticmethod
    def _key(user: User, action: Action) -> str:
        return f"{user.user_id}:{action.value}"
