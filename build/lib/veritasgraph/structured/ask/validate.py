"""Accept only one bounded, read-only SELECT over the allowed tables."""

from __future__ import annotations

from typing import Set

import sqlglot
from sqlglot import exp

from veritasgraph.structured.errors import SqlRejected

_FORBIDDEN_NODES = tuple(
    getattr(exp, name)
    for name in ("Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "AlterTable", "Command",
                 "Into", "Grant", "Revoke", "TruncateTable", "Copy", "Set", "Use", "Pragma", "Transaction",
                 "Commit", "Rollback", "Lock", "LoadData", "Attach", "Detach", "Install")
    if hasattr(exp, name)
)
DENY_FUNCTIONS = {
    # file / network / process access and stalling, across the supported engines
    "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export", "dblink",
    "dblink_exec", "pg_sleep", "sleep", "benchmark", "load_file", "sys_exec", "sys_eval",
    "read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto", "read_text", "read_blob",
    "glob", "parquet_scan", "query_table", "query",
    "file", "url", "s3", "s3cluster", "hdfs", "remote", "remotesecure", "mysql", "postgresql", "jdbc", "odbc",
    "executable", "input", "load_extension", "readfile", "writefile", "edit", "fts3_tokenizer",
}


def _limit_value(select: exp.Select) -> int | None:
    limit = select.args.get("limit")
    node = limit.expression if limit is not None else None
    return int(node.this) if isinstance(node, exp.Literal) and node.is_int else None


def validate(sql: str, dialect: str, allowed_tables: Set[str], row_cap: int) -> str:
    try:
        statements = [s for s in sqlglot.parse(sql.strip().rstrip(";"), read=dialect) if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise SqlRejected(f"SQL does not parse: {str(exc).splitlines()[0]}") from exc
    if len(statements) != 1:
        raise SqlRejected("Exactly one statement is allowed.")
    stmt = statements[0]
    if not isinstance(stmt, exp.Query):
        raise SqlRejected("Only SELECT queries are allowed.")
    for node in stmt.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            raise SqlRejected(f"{type(node).__name__} is not allowed.")
    for fn in stmt.find_all(exp.Func):
        name = (fn.name if isinstance(fn, exp.Anonymous) else fn.sql_name()).lower()
        if name in DENY_FUNCTIONS:
            raise SqlRejected(f"Function {name}() is not allowed.")

    ctes = {c.alias_or_name.lower() for c in stmt.find_all(exp.CTE)}
    for table in stmt.find_all(exp.Table):
        name = table.name.lower()
        if not name:
            raise SqlRejected("Table functions are not allowed.")
        if table.catalog:
            raise SqlRejected("Cross-catalog references are not allowed.")
        if not table.db and name in ctes:
            continue
        full = f"{table.db}.{name}".lower() if table.db else name
        if full not in allowed_tables:
            raise SqlRejected(f"Table {full} is not in the retrieved context.")

    if isinstance(stmt, exp.Select):
        current = _limit_value(stmt)
        if current is None or current > row_cap:
            stmt = stmt.limit(row_cap)
    else:  # UNION / INTERSECT / EXCEPT
        stmt = exp.select("*").from_(stmt.subquery("q")).limit(row_cap)
    return stmt.sql(dialect=dialect)
