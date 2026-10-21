"""TC-20/TC-22 — Audit integrity depth: wrong-key and anchor semantics (P3).

Complements test_audit.py. These assert the honest, conditional nature of the
tamper-evidence guarantee: it binds to the *key*, and anchors distinguish
legitimate growth from rollback.
"""

from __future__ import annotations

from medtrust.governance import AuditLog


def _populate(log: AuditLog, n: int) -> None:
    for i in range(n):
        log.append(actor=f"u{i}", action="review", decision="approved", ts=1000.0 + i)


def test_wrong_key_rejects_a_valid_log():
    """A verifier with the wrong key must reject an otherwise-valid chain."""
    log = AuditLog(key=b"key-A")
    _populate(log, 3)
    assert log.verify() is True

    # Rebind the same entries to a different key: recomputation no longer matches.
    forger = AuditLog(key=b"key-B")
    forger._entries = log._entries  # same content, wrong key
    assert forger.verify() is False


def test_extension_after_anchor_is_not_a_false_alarm():
    """Appending valid entries after an anchor must verify against that anchor."""
    log = AuditLog(key=b"k")
    _populate(log, 2)
    anchor = log.anchor()
    _populate(log, 3)  # legitimate growth
    assert log.detect_truncation(anchor) is False
    assert log.detect_rollback(anchor) is False
    assert log.verify_against_anchor(anchor) is True


def test_truncation_below_anchor_is_detected():
    log = AuditLog(key=b"k")
    _populate(log, 5)
    anchor = log.anchor()
    log._entries = log._entries[:2]  # tail truncation
    assert log.detect_truncation(anchor) is True
    assert log.verify_against_anchor(anchor) is False


def test_rollback_to_prefix_is_detected():
    log = AuditLog(key=b"k")
    _populate(log, 5)
    anchor = log.anchor()
    # Roll back to a shorter prefix and re-grow with different content.
    log._entries = log._entries[:3]
    log.append(actor="attacker", action="review", decision="approved", ts=9000.0)
    assert log.detect_rollback(anchor) is True
    assert log.verify_against_anchor(anchor) is False
