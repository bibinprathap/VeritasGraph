"""Tables in the ``vg_structured`` Postgres schema (SQLAlchemy Core)."""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

SCHEMA = "vg_structured"
metadata = sa.MetaData(schema=SCHEMA)

STATUSES = ("proposed", "accepted", "certified", "rejected", "deprecated")
ROLES = ("id", "measure", "dimension", "time", "text", "other")


def _id() -> sa.Column:
    return sa.Column("id", sa.String(32), primary_key=True)


def _stamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _status() -> sa.Column:
    return sa.Column("status", sa.String(16), nullable=False, server_default="proposed")


connection = sa.Table(
    "connection", metadata,
    _id(),
    sa.Column("name", sa.String(120), nullable=False, unique=True),
    sa.Column("dialect", sa.String(32), nullable=False),
    sa.Column("dsn_encrypted", sa.LargeBinary, nullable=False),
    sa.Column("dsn_display", sa.String(500), nullable=False),
    sa.Column("options", JSONB, nullable=False, server_default="{}"),
    sa.Column("owner", sa.String(80), nullable=False),
    *_stamps(),
)

dataset = sa.Table(
    "dataset", metadata,
    _id(),
    sa.Column("connection_id", sa.String(32), sa.ForeignKey("connection.id", ondelete="CASCADE"), nullable=False),
    sa.Column("schema_name", sa.String(255), nullable=False),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("kind", sa.String(8), nullable=False),  # table | view
    sa.Column("row_count", sa.BigInteger),
    sa.Column("comment", sa.Text),
    sa.Column("content_hash", sa.String(64), nullable=False),
    sa.Column("is_bridge", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.UniqueConstraint("connection_id", "schema_name", "name"),
)

field = sa.Table(
    "field", metadata,
    _id(),
    sa.Column("dataset_id", sa.String(32), sa.ForeignKey("dataset.id", ondelete="CASCADE"), nullable=False),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("ordinal", sa.Integer, nullable=False),
    sa.Column("data_type", sa.String(120), nullable=False),
    sa.Column("nullable", sa.Boolean, nullable=False),
    sa.Column("is_pk", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("comment", sa.Text),
    sa.Column("role", sa.String(16)),
    sa.Column("role_origin", sa.String(8)),  # llm | manual
    sa.Column("pii_class", sa.String(32)),
    sa.Column("sample", JSONB, nullable=False, server_default="[]"),
    sa.UniqueConstraint("dataset_id", "name"),
)

term = sa.Table(
    "term", metadata,
    _id(),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("definition", sa.Text, nullable=False, server_default=""),
    sa.Column("synonyms", ARRAY(sa.Text), nullable=False, server_default="{}"),
    _status(),
    sa.Column("origin", sa.String(8), nullable=False),  # llm | manual
    sa.Column("owner", sa.String(80), nullable=False),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    *_stamps(),
)
sa.Index("term_name_lower_uq", sa.func.lower(term.c.name), unique=True)

term_binding = sa.Table(
    "term_binding", metadata,
    sa.Column("term_id", sa.String(32), sa.ForeignKey("term.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("dataset_id", sa.String(32), sa.ForeignKey("dataset.id", ondelete="CASCADE"), primary_key=True),
)

relationship = sa.Table(
    "relationship", metadata,
    _id(),
    sa.Column("from_field_id", sa.String(32), sa.ForeignKey("field.id", ondelete="CASCADE"), nullable=False),
    sa.Column("to_field_id", sa.String(32), sa.ForeignKey("field.id", ondelete="CASCADE"), nullable=False),
    sa.Column("origin", sa.String(10), nullable=False),  # declared | inferred | manual
    sa.Column("confidence", sa.Float, nullable=False),
    sa.Column("evidence", JSONB, nullable=False, server_default="{}"),
    _status(),
    *_stamps(),
    sa.UniqueConstraint("from_field_id", "to_field_id"),
)

measure = sa.Table(
    "measure", metadata,
    _id(),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("description", sa.Text, nullable=False, server_default=""),
    sa.Column("expression", sa.Text, nullable=False),
    sa.Column("dataset_id", sa.String(32), sa.ForeignKey("dataset.id", ondelete="CASCADE"), nullable=False),
    sa.Column("grain", sa.Text),
    _status(),
    sa.Column("owner", sa.String(80), nullable=False),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    *_stamps(),
)
sa.Index("measure_name_lower_uq", sa.func.lower(measure.c.name), unique=True)

embedding = sa.Table(
    "embedding", metadata,
    sa.Column("object_type", sa.String(16), primary_key=True),  # term | measure | dataset | field
    sa.Column("object_id", sa.String(32), primary_key=True),
    sa.Column("text_hash", sa.String(64), nullable=False),
    sa.Column("vector", Vector(), nullable=False),  # dimension fixed at runtime (search.ensure_index)
)

index_meta = sa.Table(
    "index_meta", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("model", sa.String(200), nullable=False),
    sa.Column("dim", sa.Integer, nullable=False),
    sa.Column("query_prefix", sa.Text, nullable=False),
    sa.Column("doc_prefix", sa.Text, nullable=False),
    sa.CheckConstraint("id = 1", name="index_meta_single_row"),
)

job = sa.Table(
    "job", metadata,
    _id(),
    sa.Column("kind", sa.String(16), nullable=False),  # sync | compile | reindex
    sa.Column("connection_id", sa.String(32), sa.ForeignKey("connection.id", ondelete="CASCADE")),
    sa.Column("status", sa.String(10), nullable=False, server_default="queued"),
    sa.Column("requested_by", sa.String(80), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True)),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("stats", JSONB, nullable=False, server_default="{}"),
    sa.Column("error", sa.Text),
)

answer = sa.Table(
    "answer", metadata,
    _id(),
    sa.Column("question", sa.Text, nullable=False),
    sa.Column("actor", sa.String(80), nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("sql", sa.Text),
    sa.Column("receipt", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
)

audit = sa.Table(
    "audit", metadata,
    sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
    sa.Column("actor", sa.String(80), nullable=False),
    sa.Column("action", sa.String(40), nullable=False),
    sa.Column("object_type", sa.String(16), nullable=False),
    sa.Column("object_id", sa.String(32), nullable=False),
    sa.Column("before", JSONB),
    sa.Column("after", JSONB),
    sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
)
