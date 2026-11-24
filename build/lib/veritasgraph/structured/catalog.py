"""Reflect a source into the store; only changed datasets are re-profiled."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Tuple

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from veritasgraph import pii
from veritasgraph.structured import config, secrets
from veritasgraph.structured.connectors import DatasetInfo, Source
from veritasgraph.structured.errors import NotFound
from veritasgraph.structured.store import db
from veritasgraph.structured.store import schema as t

_SAMPLE_PER_FIELD = 5
_SKIP_SAMPLE_TYPES = ("BLOB", "BYTEA", "BINARY", "VARBINARY", "GEOMETRY", "JSON", "ARRAY", "MAP", "STRUCT")


def open_source(connection_id: str) -> Tuple[Any, Source]:
    with db.tx() as conn:
        row = conn.execute(sa.select(t.connection).where(t.connection.c.id == connection_id)).first()
    if row is None:
        raise NotFound(f"connection {connection_id} not found")
    return row, Source(secrets.unseal(row.dsn_encrypted))


def _profile(src: Source, info: DatasetInfo) -> Dict[str, Any]:
    cols = [f.name for f in info.fields if not any(x in f.data_type.upper() for x in _SKIP_SAMPLE_TYPES)]
    rows = src.sample_rows(info.schema, info.name, cols, config.sample_rows()) if cols else []
    per_col: Dict[str, List[Any]] = {c: [] for c in cols}
    for row in rows:
        for c, v in zip(cols, row):
            if v is not None and v not in per_col[c] and len(per_col[c]) < _SAMPLE_PER_FIELD * 4:
                per_col[c].append(v)
    fields = []
    for f in info.fields:
        values = per_col.get(f.name, [])
        cls = pii.classify_column(f.name, values)
        fields.append({**f.__dict__, "pii_class": cls, "sample": pii.mask_samples(values, cls, _SAMPLE_PER_FIELD)})
    return {"row_count": src.row_count(info.schema, info.name), "fields": fields}


def sync(connection_id: str) -> Dict[str, Any]:
    conn_row, src = open_source(connection_id)
    opts = conn_row.options or {}
    infos = src.reflect(include=opts.get("schemas") or None, exclude=opts.get("exclude_schemas") or ())

    with db.tx() as conn:
        existing = {
            (r.schema_name, r.name): r
            for r in conn.execute(sa.select(t.dataset).where(t.dataset.c.connection_id == connection_id))
        }

    # Profile outside any store transaction: source queries can be slow.
    changed: List[Tuple[DatasetInfo, str, Dict[str, Any]]] = []
    unchanged: List[str] = []
    for info in infos:
        old = existing.get((info.schema, info.name))
        digest = info.content_hash()
        if old is not None and old.content_hash == digest:
            unchanged.append(old.id)
            continue
        changed.append((info, digest, _profile(src, info)))

    seen = {(i.schema, i.name) for i in infos}
    removed = [r.id for k, r in existing.items() if k not in seen]
    now = _dt.datetime.now(_dt.timezone.utc)
    changed_ids: List[str] = []

    with db.tx() as conn:
        if removed:
            conn.execute(sa.delete(t.embedding).where(t.embedding.c.object_id.in_(removed)))
            conn.execute(sa.delete(t.dataset).where(t.dataset.c.id.in_(removed)))
        if unchanged:
            conn.execute(sa.update(t.dataset).where(t.dataset.c.id.in_(unchanged)).values(synced_at=now))
        for info, digest, prof in changed:
            ds_id = _upsert_dataset(conn, connection_id, info, digest, prof, now)
            changed_ids.append(ds_id)
        _declared_relationships(conn, connection_id, [c[0] for c in changed])

    return {
        "added": sum(1 for i, _, _ in changed if (i.schema, i.name) not in existing),
        "changed": sum(1 for i, _, _ in changed if (i.schema, i.name) in existing),
        "unchanged": len(unchanged),
        "removed": len(removed),
        "changed_dataset_ids": changed_ids,
    }


def _upsert_dataset(conn: sa.Connection, connection_id: str, info: DatasetInfo, digest: str,
                    prof: Dict[str, Any], now: _dt.datetime) -> str:
    stmt = pg_insert(t.dataset).values(
        id=db.new_id("ds"), connection_id=connection_id, schema_name=info.schema, name=info.name,
        kind=info.kind, row_count=prof["row_count"], comment=info.comment, content_hash=digest, synced_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["connection_id", "schema_name", "name"],
        set_={"kind": stmt.excluded.kind, "row_count": stmt.excluded.row_count, "comment": stmt.excluded.comment,
              "content_hash": stmt.excluded.content_hash, "synced_at": now},
    ).returning(t.dataset.c.id)
    ds_id = conn.execute(stmt).scalar_one()

    names = [f["name"] for f in prof["fields"]]
    conn.execute(sa.delete(t.field).where(t.field.c.dataset_id == ds_id, t.field.c.name.not_in(names)))
    for f in prof["fields"]:
        ins = pg_insert(t.field).values(
            id=db.new_id("fld"), dataset_id=ds_id, name=f["name"], ordinal=f["ordinal"], data_type=f["data_type"],
            nullable=f["nullable"], is_pk=f["is_pk"], comment=f["comment"], pii_class=f["pii_class"], sample=f["sample"],
        )
        conn.execute(ins.on_conflict_do_update(
            index_elements=["dataset_id", "name"],
            # role / role_origin are left alone: manual edits survive re-syncs.
            set_={k: ins.excluded[k] for k in ("ordinal", "data_type", "nullable", "is_pk", "comment", "pii_class", "sample")},
        ))
    return ds_id


def _declared_relationships(conn: sa.Connection, connection_id: str, infos: List[DatasetInfo]) -> None:
    lookup = {
        (r.schema_name, r.dataset, r.field): r.id
        for r in conn.execute(
            sa.select(t.dataset.c.schema_name, t.dataset.c.name.label("dataset"), t.field.c.name.label("field"), t.field.c.id)
            .join(t.field, t.field.c.dataset_id == t.dataset.c.id)
            .where(t.dataset.c.connection_id == connection_id)
        )
    }
    for info in infos:
        for fk in info.foreign_keys:
            for col, ref_col in zip(fk.columns, fk.ref_columns):
                src_id = lookup.get((info.schema, info.name, col))
                dst_id = lookup.get((fk.ref_schema, fk.ref_table, ref_col))
                if src_id and dst_id:
                    conn.execute(pg_insert(t.relationship).values(
                        id=db.new_id("rel"), from_field_id=src_id, to_field_id=dst_id, origin="declared",
                        confidence=1.0, evidence={"declared": True}, status="accepted",
                    ).on_conflict_do_nothing())
