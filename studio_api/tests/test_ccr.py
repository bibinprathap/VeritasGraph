"""Tests for the ported headroom CCR store (studio_api/ccr.py).

These mirror the unit tests of the Rust reference implementation vendored at
studio_api/vendor/headroom/ to confirm the port preserves the semantics.
"""

from __future__ import annotations

import time

from studio_api.ccr import (
    InMemoryCcrStore,
    compute_key,
    marker_for,
)


def test_compute_key_is_24_hex_chars():
    key = compute_key("hello world")
    assert len(key) == 24
    assert all(c in "0123456789abcdef" for c in key)


def test_compute_key_is_deterministic():
    assert compute_key("the same payload") == compute_key("the same payload")


def test_compute_key_diverges_for_different_payloads():
    assert compute_key("alpha") != compute_key("beta")


def test_marker_format_is_pinned():
    assert marker_for("abc123") == "<<ccr:abc123>>"


def test_put_then_get_returns_payload():
    store = InMemoryCcrStore()
    store.put("abc123", '[{"id":1}]')
    assert store.get("abc123") == '[{"id":1}]'


def test_missing_hash_returns_none():
    assert InMemoryCcrStore().get("never_stored") is None


def test_put_overwrites_under_same_hash():
    store = InMemoryCcrStore()
    store.put("h", "first")
    store.put("h", "second")
    assert store.get("h") == "second"
    assert len(store) == 1


def test_capacity_evicts_oldest():
    store = InMemoryCcrStore(capacity=2)
    store.put("a", "1")
    store.put("b", "2")
    store.put("c", "3")
    assert len(store) == 2
    assert store.get("a") is None
    assert store.get("b") == "2"
    assert store.get("c") == "3"


def test_expired_entries_are_dropped_on_get():
    store = InMemoryCcrStore(capacity=10, ttl_seconds=0.01)
    store.put("a", "1")
    time.sleep(0.025)
    assert store.get("a") is None
    assert len(store) == 0
