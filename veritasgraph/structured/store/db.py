from __future__ import annotations

import uuid
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Optional

import sqlalchemy as sa

from veritasgraph.structured import config
from veritasgraph.structured.store import schema as t

_MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


@lru_cache(maxsize=1)
def engine() -> sa.Engine:
    dsn = config.dsn()
    if not dsn:
        raise RuntimeError("VG_STRUCTURED_DSN is not set")
    if not dsn.startswith("postgresql"):
        raise RuntimeError("VG_STRUCTURED_DSN must be a postgresql+psycopg:// URL")
    return sa.create_engine(dsn, pool_pre_ping=True, pool_size=5, max_overflow=5)


@contextmanager
def tx() -> Iterator[sa.Connection]:
    with engine().begin() as conn:
        yield conn


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def audit(conn: sa.Connection, actor: str, action: str, object_type: str, object_id: str,
          before: Optional[dict[str, Any]] = None, after: Optional[dict[str, Any]] = None) -> None:
    conn.execute(sa.insert(t.audit).values(
        actor=actor, action=action, object_type=object_type, object_id=object_id, before=before, after=after,
    ))


def upgrade() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS))
    cfg.set_main_option("sqlalchemy.url", config.dsn() or "")
    command.upgrade(cfg, "head")
