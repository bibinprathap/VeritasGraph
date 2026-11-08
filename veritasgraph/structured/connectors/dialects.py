"""Per-engine facts. Reflection itself is generic (SQLAlchemy Inspector)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from sqlalchemy.engine import make_url

from veritasgraph.structured.errors import Invalid


@dataclass(frozen=True)
class Dialect:
    name: str
    sqlglot: str
    drivers: Tuple[str, ...]
    file_based: bool = False
    extra: Optional[str] = None  # pip extra that provides the driver
    session_sql: Tuple[str, ...] = ()  # run on every read-only connection; {ms} / {s} are filled in
    explain_prefix: str = "EXPLAIN "
    system_schemas: Tuple[str, ...] = ("information_schema",)
    connect_args: Dict[str, object] = field(default_factory=dict)


DIALECTS: Dict[str, Dialect] = {
    d.name: d
    for d in (
        Dialect(
            "postgresql", "postgres", ("postgresql", "postgresql+psycopg", "postgresql+psycopg2"),
            session_sql=("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY", "SET statement_timeout = {ms}"),
            system_schemas=("information_schema", "pg_catalog", "pg_toast"),
        ),
        Dialect(
            "mysql", "mysql", ("mysql+pymysql", "mariadb+pymysql"),
            session_sql=("SET SESSION TRANSACTION READ ONLY", "SET SESSION max_execution_time = {ms}"),
            system_schemas=("information_schema", "mysql", "performance_schema", "sys"),
        ),
        Dialect("sqlite", "sqlite", ("sqlite", "sqlite+pysqlite"), file_based=True,
                session_sql=("PRAGMA query_only = ON",), explain_prefix="EXPLAIN QUERY PLAN "),
        Dialect("duckdb", "duckdb", ("duckdb",), file_based=True,
                connect_args={"read_only": True},
                system_schemas=("information_schema", "pg_catalog")),
        Dialect(
            "clickhouse", "clickhouse", ("clickhouse", "clickhouse+http", "clickhouse+native"),
            # max_execution_time must be set before readonly=1, which forbids further SETs.
            session_sql=("SET max_execution_time = {s}", "SET readonly = 1"),
            explain_prefix="EXPLAIN SYNTAX ",
            system_schemas=("system", "information_schema", "INFORMATION_SCHEMA"),
        ),
        Dialect("trino", "trino", ("trino",), explain_prefix="EXPLAIN (TYPE VALIDATE) "),
        Dialect("hive", "hive", ("hive", "hive+http", "hive+https"), extra="structured-hive",
                system_schemas=("information_schema", "sys")),
        Dialect("snowflake", "snowflake", ("snowflake",), extra="structured-saas",
                session_sql=("ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {s}",),
                explain_prefix="EXPLAIN USING TEXT ", system_schemas=("INFORMATION_SCHEMA",)),
        Dialect("databricks", "databricks", ("databricks",), extra="structured-saas",
                system_schemas=("information_schema",)),
    )
}


def dialect_for(dsn: str) -> Dialect:
    driver = make_url(dsn).drivername
    for d in DIALECTS.values():
        if driver in d.drivers:
            return d
    raise Invalid(f"Unsupported database type '{driver}'. Supported: {', '.join(DIALECTS)}")
