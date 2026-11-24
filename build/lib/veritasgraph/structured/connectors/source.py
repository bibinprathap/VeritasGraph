"""A source database: reflection, profiling, and read-only execution."""

from __future__ import annotations

import datetime as _dt
import decimal
import hashlib
import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator, List, Optional, Sequence, Tuple

import sqlalchemy as sa
from sqlalchemy.pool import NullPool

from veritasgraph.structured import config
from veritasgraph.structured.connectors.guard import check_dsn
from veritasgraph.structured.errors import Invalid


@dataclass
class FieldInfo:
    name: str
    ordinal: int
    data_type: str
    nullable: bool
    is_pk: bool
    comment: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    columns: List[str]
    ref_schema: str
    ref_table: str
    ref_columns: List[str]


@dataclass
class DatasetInfo:
    schema: str
    name: str
    kind: str
    comment: Optional[str]
    fields: List[FieldInfo]
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)

    def content_hash(self) -> str:
        payload = {"kind": self.kind, "comment": self.comment,
                   "fields": [asdict(f) for f in self.fields],
                   "fks": [asdict(fk) for fk in self.foreign_keys]}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (_dt.date, _dt.datetime, _dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    return value


class Source:
    def __init__(self, dsn: str) -> None:
        self.dialect = check_dsn(dsn)
        try:
            self.engine = sa.create_engine(dsn, poolclass=NullPool, connect_args=dict(self.dialect.connect_args))
        except sa.exc.NoSuchModuleError as exc:
            hint = f" Install the extra: pip install 'veritasgraph-mcp[{self.dialect.extra}]'" if self.dialect.extra else ""
            raise Invalid(f"No driver for {self.dialect.name}.{hint}") from exc

    # ---------------------------------------------------------------- reflection
    def test(self) -> None:
        with self.readonly() as cur:
            cur.execute("SELECT 1")
            cur.fetchall()

    def reflect(self, include: Optional[Sequence[str]] = None, exclude: Sequence[str] = ()) -> List[DatasetInfo]:
        insp = sa.inspect(self.engine)
        skip = {s.lower() for s in (*self.dialect.system_schemas, *exclude)}
        schemas = [s for s in (include or insp.get_schema_names()) if s.lower() not in skip]
        out: List[DatasetInfo] = []
        for schema in schemas:
            for kind, names in (("table", insp.get_table_names(schema=schema)),
                                ("view", _safe(lambda: insp.get_view_names(schema=schema), []))):
                for name in names:
                    out.append(self._describe(insp, schema, name, kind))
        return out

    def _describe(self, insp: sa.Inspector, schema: str, name: str, kind: str) -> DatasetInfo:
        pk = set(_safe(lambda: insp.get_pk_constraint(name, schema=schema), {}).get("constrained_columns") or [])
        cols = insp.get_columns(name, schema=schema)
        fields = [
            FieldInfo(name=c["name"], ordinal=i, data_type=str(c["type"]), nullable=bool(c.get("nullable", True)),
                      is_pk=c["name"] in pk, comment=c.get("comment"))
            for i, c in enumerate(cols)
        ]
        fks = [
            ForeignKeyInfo(fk["constrained_columns"], fk.get("referred_schema") or schema,
                           fk["referred_table"], fk["referred_columns"])
            for fk in _safe(lambda: insp.get_foreign_keys(name, schema=schema), [])
            if fk.get("referred_table")
        ]
        comment = _safe(lambda: insp.get_table_comment(name, schema=schema), {}).get("text")
        return DatasetInfo(schema, name, kind, comment, fields, fks)

    # ---------------------------------------------------------------- profiling
    def _table(self, schema: str, name: str, columns: Sequence[str]) -> sa.TableClause:
        return sa.table(name, *(sa.column(c) for c in columns), schema=schema)

    def row_count(self, schema: str, name: str) -> Optional[int]:
        stmt = sa.select(sa.func.count()).select_from(self._table(schema, name, []))
        try:
            with self.readonly() as cur:
                cur.execute(_compile(self.engine, stmt))
                return int(cur.fetchone()[0])
        except Exception:  # noqa: BLE001 - counts are best effort (timeouts on huge tables)
            return None

    def sample_rows(self, schema: str, name: str, columns: Sequence[str], n: int) -> List[Tuple[Any, ...]]:
        stmt = sa.select(*(sa.column(c) for c in columns)).select_from(self._table(schema, name, columns)).limit(n)
        with self.readonly() as cur:
            cur.execute(_compile(self.engine, stmt))
            return [tuple(jsonable(v) for v in row) for row in cur.fetchall()]

    def distinct_values(self, schema: str, name: str, column: str, n: int) -> List[Any]:
        col = sa.column(column)
        stmt = (sa.select(col).distinct().select_from(self._table(schema, name, [column]))
                .where(col.is_not(None)).limit(n))
        with self.readonly() as cur:
            cur.execute(_compile(self.engine, stmt))
            return [row[0] for row in cur.fetchall()]

    def count_contained(self, schema: str, name: str, column: str, values: List[Any]) -> int:
        if not values:
            return 0
        col = sa.column(column)
        stmt = (sa.select(sa.func.count(sa.distinct(col))).select_from(self._table(schema, name, [column]))
                .where(col.in_(values)))
        with self.readonly() as cur:
            cur.execute(_compile(self.engine, stmt))
            return int(cur.fetchone()[0])

    # ---------------------------------------------------------------- execution
    @contextmanager
    def readonly(self) -> Iterator[Any]:
        """A DBAPI cursor on a fresh connection with the dialect's read-only/timeout settings."""
        timeout = config.statement_timeout_s()
        with self.engine.connect() as conn:
            cur = conn.connection.dbapi_connection.cursor()
            try:
                for stmt in self.dialect.session_sql:
                    cur.execute(stmt.format(ms=timeout * 1000, s=timeout))
                yield cur
            finally:
                cur.close()
                conn.rollback()

    def explain(self, sql: str) -> None:
        with self.readonly() as cur:
            cur.execute(self.dialect.explain_prefix + sql)
            cur.fetchall()

    def run(self, sql: str, cap: int) -> Tuple[List[str], List[List[Any]], bool]:
        # Raw DBAPI execute with no parameters: no driver-side interpolation of % or :name.
        with self.readonly() as cur:
            cur.execute(sql)
            columns = [d[0] for d in cur.description or []]
            rows = cur.fetchmany(cap + 1)
        return columns, [[jsonable(v) for v in r] for r in rows[:cap]], len(rows) > cap


def _compile(engine: sa.Engine, stmt: sa.Select) -> str:
    """Render a Core statement with literal values (identifiers are quoted by SQLAlchemy)."""
    return str(stmt.compile(engine, compile_kwargs={"literal_binds": True}))


def _safe(fn, default):
    try:
        return fn()
    except (NotImplementedError, sa.exc.SQLAlchemyError):
        return default
