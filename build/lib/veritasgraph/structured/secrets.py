"""Connection strings are encrypted at rest and never returned in clear."""

from __future__ import annotations

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.engine import make_url


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = os.environ.get("VG_SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "VG_SECRET_KEY is not set. Generate one with: python -c "
            "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode())


def seal(text: str) -> bytes:
    return _fernet().encrypt(text.encode())


def unseal(blob: bytes) -> str:
    try:
        return _fernet().decrypt(bytes(blob)).decode()
    except InvalidToken as exc:
        raise RuntimeError("Cannot decrypt a stored connection: VG_SECRET_KEY changed?") from exc


def display_dsn(dsn: str) -> str:
    """DSN with the password hidden, for UI and logs."""
    return make_url(dsn).render_as_string(hide_password=True)
