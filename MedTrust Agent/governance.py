"""Governance / GRC layer (paper: Governance and Audit).

Policy checks, citation enforcement, and a **keyed, anchored, tamper-evident**
audit log. Mirrors ``veritas-reason`` (decision ledger + PROV-O provenance) and
the policy-compliance demo. Every governed decision appends an HMAC-chained
audit entry.

Audit integrity model (reviewer R2-3)
-------------------------------------
We make a *bounded, testable* claim rather than an absolute one. Under the
assumption that the HMAC key is secret (held outside the log; the "verifier
trust assumption"), the log is **tamper-evident**: it detects

* **content mutation** -- any change to a stored entry breaks its keyed MAC;
* **recomputation** -- an attacker without the key cannot recompute a valid
  chain, so forging consistent MACs fails;
* **truncation** -- dropping tail entries is caught by comparing against the
  last external anchor (length + head digest);
* **rollback** -- restoring an older head is caught because the anchored head
  digest no longer matches / is not an extension of the current chain.

These properties are verified by the tests in ``tests/test_audit.py``. We do
**not** claim information-theoretic or "provable" security; detection is
conditional on key secrecy and on anchors being published to an append-only,
trusted sink (e.g. a WORM store or timestamping service).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .retrieval import Evidence


@dataclass
class GovernanceResult:
    approved: bool
    reason: str
    citations: List[str] = field(default_factory=list)
    audit_id: str = ""


@dataclass(frozen=True)
class AuditEntry:
    index: int
    actor: str
    action: str
    decision: str
    ts: float
    prev_hash: str
    entry_hash: str  # keyed MAC over (index|actor|action|decision|ts|prev_hash)


@dataclass(frozen=True)
class Anchor:
    """An externally published checkpoint of the log head.

    In production this is written to an append-only / WORM sink or a
    timestamping authority. Here we model it as an immutable record the
    verifier keeps outside the log's own storage.
    """

    length: int
    head_hash: str
    ts: float


def _default_key() -> bytes:
    """Process key; production supplies a managed secret via MEDTRUST_AUDIT_KEY.

    Key secrecy is the stated trust assumption for tamper-evidence.
    """
    env = os.environ.get("MEDTRUST_AUDIT_KEY")
    if env:
        return env.encode("utf-8")
    return b"medtrust-dev-audit-key-change-me"


class AuditLog:
    """Append-only, HMAC-chained, externally anchorable audit log.

    Backwards compatible: ``append()`` returns the entry MAC, ``verify()``
    returns a bool, ``_entries`` is the entry list and ``len()`` is supported.
    New methods add keyed verification, anchoring, and explicit
    truncation/rollback detection.
    """

    GENESIS = "GENESIS"

    def __init__(self, key: bytes | None = None) -> None:
        self._entries: List[AuditEntry] = []
        self._key: bytes = key if key is not None else _default_key()
        self._anchors: List[Anchor] = []

    # -- core chain ---------------------------------------------------------
    def _mac(self, index: int, actor: str, action: str, decision: str,
             ts: float, prev: str) -> str:
        payload = f"{index}|{actor}|{action}|{decision}|{ts:.6f}|{prev}".encode()
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def append(self, actor: str, action: str, decision: str,
               ts: float | None = None) -> str:
        prev = self._entries[-1].entry_hash if self._entries else self.GENESIS
        index = len(self._entries)
        ts = time.time() if ts is None else ts
        entry_hash = self._mac(index, actor, action, decision, ts, prev)
        self._entries.append(
            AuditEntry(index, actor, action, decision, ts, prev, entry_hash)
        )
        return entry_hash

    @property
    def head(self) -> str:
        return self._entries[-1].entry_hash if self._entries else self.GENESIS

    def verify(self) -> bool:
        """Recompute the keyed chain to detect content mutation / recomputation.

        Uses ``hmac.compare_digest`` for constant-time comparison. An attacker
        without the key cannot produce a matching MAC, so any rewrite -- even a
        fully self-consistent one -- is rejected.
        """
        prev = self.GENESIS
        for e in self._entries:
            expected = self._mac(e.index, e.actor, e.action, e.decision, e.ts, prev)
            if not hmac.compare_digest(expected, e.entry_hash):
                return False
            if e.prev_hash != prev:
                return False
            prev = e.entry_hash
        return True

    # -- external anchoring -------------------------------------------------
    def anchor(self) -> Anchor:
        """Publish the current head to the external anchor set and return it."""
        a = Anchor(length=len(self._entries), head_hash=self.head, ts=time.time())
        self._anchors.append(a)
        return a

    @property
    def last_anchor(self) -> Optional[Anchor]:
        return self._anchors[-1] if self._anchors else None

    def _head_at(self, length: int) -> str:
        """Keyed head digest of the first ``length`` entries."""
        prev = self.GENESIS
        for e in self._entries[:length]:
            prev = self._mac(e.index, e.actor, e.action, e.decision, e.ts, prev)
        return prev

    def detect_truncation(self, anchor: Optional[Anchor] = None) -> bool:
        """True iff the log is shorter than / inconsistent with an anchor."""
        anchor = anchor or self.last_anchor
        if anchor is None:
            return False
        if len(self._entries) < anchor.length:
            return True
        return not hmac.compare_digest(self._head_at(anchor.length), anchor.head_hash)

    def detect_rollback(self, anchor: Optional[Anchor] = None) -> bool:
        """True iff the current chain does not extend the anchored head."""
        anchor = anchor or self.last_anchor
        if anchor is None:
            return False
        if len(self._entries) < anchor.length:
            return True
        return not hmac.compare_digest(self._head_at(anchor.length), anchor.head_hash)

    def verify_against_anchor(self, anchor: Optional[Anchor] = None) -> bool:
        """Full check: keyed chain valid AND consistent with the anchor."""
        if not self.verify():
            return False
        if self.detect_truncation(anchor):
            return False
        if self.detect_rollback(anchor):
            return False
        return True

    def __len__(self) -> int:
        return len(self._entries)


# Content that must never appear in an answer (regulated / unsafe). Expanded
# with prompt-injection families used by the adversarial suite (paper: Security).
_BLOCKED_PHRASES = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard the above",
    "reveal system prompt",
    "reveal the system prompt",
    "print your instructions",
    "exfiltrate",
    "send patient data to",
)


class GovernanceEngine:
    """Enforces citation requirements and content policy, and writes the audit trail."""

    def __init__(self, audit: AuditLog | None = None) -> None:
        # Use identity check, not truthiness: an empty AuditLog has len 0 and is
        # falsy, so ``audit or AuditLog()`` would silently discard a caller's log.
        self.audit = audit if audit is not None else AuditLog()

    def review(
        self, actor: str, answer: str, evidence: Sequence[Evidence]
    ) -> GovernanceResult:
        lowered = answer.lower()
        for phrase in _BLOCKED_PHRASES:
            if phrase in lowered:
                audit_id = self.audit.append(actor, "review", "blocked:policy")
                return GovernanceResult(False, f"blocked content: '{phrase}'", [], audit_id)

        if not evidence:
            audit_id = self.audit.append(actor, "review", "blocked:no_citation")
            return GovernanceResult(
                False, "refused: no grounded citation available", [], audit_id
            )

        citations = [ev.citation for ev in evidence]
        audit_id = self.audit.append(actor, "review", "approved")
        return GovernanceResult(True, "approved", citations, audit_id)
