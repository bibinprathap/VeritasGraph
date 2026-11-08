"""Bearer-token authentication and role checks for the Studio API.

Configure with ``STUDIO_API_TOKENS="<token>:<role>,<token>:<role>"`` where role
is ``viewer``, ``editor`` or ``admin``. Set ``STUDIO_AUTH=off`` only for local
development; the server refuses to start with neither setting present, so it can
never be exposed (e.g. through a public tunnel) without authentication by
accident.

Role model:

* ``viewer`` — read anything; ask questions (graph query, playground chat,
  answerability checks).
* ``editor`` — everything a viewer can do, plus create/update/delete Studio
  resources, ingest and import documents, propose ontology entries.
* ``admin``  — everything, including wiping the graph and certifying ontology.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from functools import lru_cache
from typing import Dict, Optional

from fastapi import HTTPException, Request, status

log = logging.getLogger("studio_api.security")

ROLES = ("viewer", "editor", "admin")
_RANK = {role: i for i, role in enumerate(ROLES)}
_MIN_TOKEN_LEN = 24

# POST routes that only read graph data or run a conversation, so a viewer may
# call them.
_VIEWER_POSTS = frozenset(
    {
        "/graphrag/query",
        "/graphrag/answerable",
        "/playground/chat",
    }
)


@lru_cache(maxsize=1)
def _tokens() -> Dict[str, str]:
    tokens: Dict[str, str] = {}
    for item in os.environ.get("STUDIO_API_TOKENS", "").split(","):
        token, _, role = item.strip().partition(":")
        token = token.strip()
        if not token:
            continue
        role = (role or "viewer").strip().lower()
        if role not in _RANK:
            raise RuntimeError(f"Unknown role '{role}' in STUDIO_API_TOKENS")
        if len(token) < _MIN_TOKEN_LEN:
            raise RuntimeError(
                f"STUDIO_API_TOKENS entries must be at least {_MIN_TOKEN_LEN} characters"
            )
        tokens[token] = role
    return tokens


def auth_disabled() -> bool:
    return os.environ.get("STUDIO_AUTH", "").strip().lower() == "off"


def check_config() -> None:
    """Fail fast instead of silently running an open server."""
    if auth_disabled():
        log.warning("STUDIO_AUTH=off: the Studio API is running WITHOUT authentication.")
        return
    if not _tokens():
        raise RuntimeError(
            "Studio API authentication is not configured. Set STUDIO_API_TOKENS "
            "(e.g. '<random-32-char-token>:admin') or STUDIO_AUTH=off for local development."
        )


def role_at_least(role: str, needed: str) -> bool:
    return _RANK.get(role, -1) >= _RANK[needed]


def required_role(method: str, path: str) -> str:
    """The minimum role for an HTTP route.

    MCP bridge routes return ``viewer`` here; the bridge applies a per-tool
    check (see :mod:`studio_api.routes.mcp`) because one endpoint can run tools
    with very different blast radius.
    """
    method = method.upper()
    if method in {"GET", "HEAD", "OPTIONS"} or path in _VIEWER_POSTS:
        return "viewer"
    if path.startswith("/mcp/"):
        return "viewer"
    # Anyone who can read an answer may rate it.
    if path.startswith("/graphrag/answers/") and path.endswith("/feedback"):
        return "viewer"
    if method == "DELETE" and path.startswith("/graphrag"):
        return "admin"
    if path.startswith("/ontology") and path.endswith(("/certify", "/deprecate")):
        return "admin"
    if path.startswith("/graphrag/snapshots") and path.endswith("/restore"):
        return "admin"
    return "editor"


def _role_for(token: str) -> Optional[str]:
    match: Optional[str] = None
    candidate = token.encode()
    for known, role in _tokens().items():
        # Compare against every token so timing does not reveal which one matched.
        if hmac.compare_digest(known.encode(), candidate):
            match = role
    return match


def caller_role(request: Request) -> str:
    """The authenticated role set by :func:`authorize` (``admin`` when auth is off)."""
    return getattr(request.state, "role", "admin" if auth_disabled() else "viewer")


def caller_actor(request: Request) -> str:
    """A stable, non-secret caller id for audit records (role + token fingerprint)."""
    return getattr(request.state, "actor", "local" if auth_disabled() else "anonymous")


def authorize(request: Request) -> str:
    """FastAPI dependency: authenticate the caller and enforce the route's role."""
    if auth_disabled():
        request.state.role = "admin"
        request.state.actor = "local"
        return "admin"
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = _role_for(token)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    needed = required_role(request.method, request.url.path)
    if not role_at_least(role, needed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' cannot perform this action (needs '{needed}')",
        )
    request.state.role = role
    request.state.actor = f"{role}:{hashlib.sha256(token.encode()).hexdigest()[:12]}"
    return role
