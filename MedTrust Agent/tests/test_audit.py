"""Audit integrity tests (reviewer R2-3).

Validates the keyed, anchored, tamper-evident audit log against the three
attacks the reviewer asked us to test explicitly: **truncation**,
**recomputation**, and **rollback** -- plus content mutation and the
key-secrecy assumption.
"""

import copy

from medtrust.governance import AuditLog, AuditEntry


def _populate(log: AuditLog, n: int = 5) -> None:
    for i in range(n):
        log.append(f"actor{i}", "review", "approved" if i % 2 else "blocked:policy")


# --- baseline integrity ----------------------------------------------------

def test_clean_log_verifies():
    log = AuditLog(key=b"k")
    _populate(log)
    assert log.verify() is True
    assert len(log) == 5


def test_content_mutation_is_detected():
    log = AuditLog(key=b"k")
    _populate(log)
    object.__setattr__(log._entries[2], "decision", "approved-TAMPERED")
    assert log.verify() is False


# --- R2-3 (a) truncation ---------------------------------------------------

def test_truncation_is_detected_via_anchor():
    log = AuditLog(key=b"k")
    _populate(log, 5)
    anchor = log.anchor()               # external checkpoint at length 5
    # Attacker drops the last two entries to hide activity.
    del log._entries[3:]
    assert len(log) == 3
    # The surviving chain still "verifies" internally...
    assert log.verify() is True
    # ...but truncation is caught against the published anchor.
    assert log.detect_truncation(anchor) is True
    assert log.verify_against_anchor(anchor) is False


# --- R2-3 (b) recomputation ------------------------------------------------

def test_recomputation_without_key_is_detected():
    """Attacker edits an entry and recomputes the WHOLE chain, but lacks the key."""
    log = AuditLog(key=b"secret-key")
    _populate(log, 4)

    # Simulate an attacker who can read storage and recompute a *self-consistent*
    # chain with a GUESSED key, then swap in their forged entries.
    forged = AuditLog(key=b"wrong-guessed-key")
    forged.append("actorX", "review", "blocked:policy")  # changed history
    for i in range(1, 4):
        forged.append(f"actor{i}", "review", "approved")
    log._entries = forged._entries  # install the recomputed chain

    # Verified under the REAL key: the forged MACs don't match -> detected.
    assert log.verify() is False


def test_recomputation_with_key_would_pass_documents_assumption():
    """If the key leaks, recomputation is undetectable -- the stated assumption."""
    key = b"leaked-key"
    log = AuditLog(key=key)
    _populate(log, 3)
    attacker = AuditLog(key=key)                 # attacker HAS the key
    attacker.append("ghost", "review", "approved")
    attacker.append("ghost", "review", "approved")
    attacker.append("ghost", "review", "approved")
    log._entries = attacker._entries
    # With the key, the forgery verifies -> confirms tamper-evidence is
    # conditional on key secrecy (documented, not "provable").
    assert log.verify() is True


# --- R2-3 (c) rollback -----------------------------------------------------

def test_rollback_is_detected_via_anchor():
    log = AuditLog(key=b"k")
    _populate(log, 3)
    snapshot = copy.deepcopy(log._entries)      # old state
    log.append("actor3", "review", "approved")
    log.append("actor4", "review", "blocked:policy")
    anchor = log.anchor()                        # anchor at length 5
    # Attacker rolls back to the 3-entry state to erase the last two decisions.
    log._entries = snapshot
    assert log.detect_rollback(anchor) is True
    assert log.verify_against_anchor(anchor) is False


def test_extension_after_anchor_still_valid():
    """Legitimate appends after an anchor must NOT be flagged as tampering."""
    log = AuditLog(key=b"k")
    _populate(log, 3)
    anchor = log.anchor()
    log.append("actor3", "review", "approved")   # honest continuation
    assert log.detect_truncation(anchor) is False
    assert log.detect_rollback(anchor) is False
    assert log.verify_against_anchor(anchor) is True
