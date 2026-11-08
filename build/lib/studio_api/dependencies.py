"""Request-scoped dependencies for the studio API."""

from __future__ import annotations

from studio_api.store import StudioStore, store


def get_store() -> StudioStore:
    """Return the process-wide studio store singleton."""
    return store
