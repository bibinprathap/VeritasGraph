"""Faithful Python port of headroom's CCR (Compress-Cache-Retrieve) store.

This is a line-for-line port of the Rust reference implementation vendored at
``studio_api/vendor/headroom/`` (``ccr_mod.rs`` + ``ccr_in_memory.rs``, from
https://github.com/chopratejas/headroom). The semantics are preserved exactly:

* ``compute_key`` — BLAKE3 of the payload, first 24 hex chars (96 bits).
* ``marker_for`` — the fixed ``<<ccr:HASH>>`` marker injected into compressed
  content so the original bytes can be retrieved later.
* :class:`InMemoryCcrStore` — process-local store with:
    - lazy TTL expiry on ``get`` (no background reaper),
    - capacity-bound FIFO eviction of the oldest entry on ``put``,
    - idempotent re-store fast-path (same hash overwrites in place),
    - thread-safety via a lock (the Python GIL + lock stands in for DashMap's
      sharded concurrency; behaviour is identical, only the contention profile
      differs).

The store is *lossy on the wire, lossless end-to-end*: a transform drops bulky
content from the prompt but stashes the original here keyed by its hash, and the
runtime serves it back on a retrieval call.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Optional

try:  # Prefer real BLAKE3 to match headroom's keys byte-for-byte.
    from blake3 import blake3 as _blake3  # type: ignore

    def _hash_hex(payload: bytes) -> str:
        return _blake3(payload).hexdigest()

except ImportError:  # Fall back to stdlib BLAKE2b when blake3 isn't installed.
    import hashlib

    def _hash_hex(payload: bytes) -> str:
        return hashlib.blake2b(payload).hexdigest()


# Default capacity — matches headroom's `DEFAULT_CAPACITY`.
DEFAULT_CAPACITY = 1000

# Default TTL — 30 minutes, matching headroom's `DEFAULT_TTL`.
DEFAULT_TTL_SECONDS = 1800.0


def compute_key(payload: bytes | str) -> str:
    """Canonical CCR key: BLAKE3 → first 24 hex chars (96 bits).

    Port of headroom ``compute_key``. The 24-char prefix matches the
    tool-injection regex ``[a-f0-9]{24}``.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return _hash_hex(payload)[:24]


def marker_for(hash_: str) -> str:
    """The fixed ``<<ccr:HASH>>`` marker. Port of headroom ``marker_for``."""
    return f"<<ccr:{hash_}>>"


class _Entry:
    __slots__ = ("payload", "inserted")

    def __init__(self, payload: str, inserted: float) -> None:
        self.payload = payload
        self.inserted = inserted


class InMemoryCcrStore:
    """Process-local CCR store. Python port of headroom's ``InMemoryCcrStore``.

    Lazy TTL expiry on read; capacity-bound FIFO eviction on write; idempotent
    re-store. An :class:`~collections.OrderedDict` supplies both the map and the
    FIFO insertion order that the Rust version splits across ``DashMap`` + a
    ``VecDeque``.
    """

    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._map: "OrderedDict[str, _Entry]" = OrderedDict()
        self._ttl = ttl_seconds
        self._capacity = capacity
        self._lock = threading.RLock()

    def _evict_until_under_capacity(self) -> None:
        """Evict oldest entries until under capacity. Port of the Rust sweep."""
        while len(self._map) >= self._capacity:
            try:
                self._map.popitem(last=False)  # FIFO: drop the oldest.
            except KeyError:
                break

    def put(self, hash_: str, payload: str) -> None:
        """Stash ``payload`` under ``hash_``; idempotent re-store overwrites."""
        with self._lock:
            existing = self._map.get(hash_)
            if existing is not None:
                # Idempotent re-store fast-path: overwrite in place, keep order.
                existing.payload = payload
                existing.inserted = time.monotonic()
                return

            if len(self._map) >= self._capacity:
                self._evict_until_under_capacity()

            self._map[hash_] = _Entry(payload, time.monotonic())

    def get(self, hash_: str) -> Optional[str]:
        """Look up ``hash_``; returns ``None`` if missing or expired (lazy)."""
        with self._lock:
            entry = self._map.get(hash_)
            if entry is None:
                return None
            if time.monotonic() - entry.inserted <= self._ttl:
                return entry.payload
            # Expired — evict and report miss.
            self._map.pop(hash_, None)
            return None

    def __len__(self) -> int:
        with self._lock:
            return len(self._map)

    def is_empty(self) -> bool:
        return len(self) == 0
