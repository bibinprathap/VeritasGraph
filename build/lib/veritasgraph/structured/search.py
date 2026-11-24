"""Embedding index (pgvector, HNSW cosine) + trigram name match, fused by reciprocal rank."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from veritasgraph.llm import Embedder, rerank
from veritasgraph.structured.errors import IndexMismatch
from veritasgraph.structured.store import schema as t

KINDS = ("term", "measure", "dataset", "field")
_RRF_K = 60


@dataclass
class Hit:
    kind: str
    id: str
    name: str
    score: float
    similarity: float = 0.0   # cosine, 0..1
    name_match: float = 0.0   # trigram word similarity, 0..1
    connection_id: Optional[str] = None


# ------------------------------------------------------------------ index
def ensure_index(conn: sa.Connection, emb: Embedder) -> None:
    sig = emb.signature()
    meta = conn.execute(sa.select(t.index_meta)).first()
    if meta is None:
        conn.execute(sa.insert(t.index_meta).values(id=1, **sig))
        conn.execute(sa.text(f"ALTER TABLE {t.SCHEMA}.embedding ALTER COLUMN vector TYPE vector({int(sig['dim'])})"))
        conn.execute(sa.text(
            f"CREATE INDEX IF NOT EXISTS embedding_hnsw ON {t.SCHEMA}.embedding USING hnsw (vector vector_cosine_ops)"))
        return
    current = {k: getattr(meta, k) for k in sig}
    if current != sig:
        raise IndexMismatch(
            f"Embedding settings changed from {current['model']} ({current['dim']}-d) to "
            f"{sig['model']} ({sig['dim']}-d). Run `veritasgraph structured reindex` (admin)."
        )


def reset_index(conn: sa.Connection) -> None:
    conn.execute(sa.text(f"DROP INDEX IF EXISTS {t.SCHEMA}.embedding_hnsw"))
    conn.execute(sa.delete(t.embedding))
    conn.execute(sa.delete(t.index_meta))
    conn.execute(sa.text(f"ALTER TABLE {t.SCHEMA}.embedding ALTER COLUMN vector TYPE vector"))


def _texts(conn: sa.Connection, kind: str, ids: Optional[Sequence[str]]) -> Dict[str, str]:
    def where(col):
        return col.in_(ids) if ids is not None else sa.true()

    if kind == "term":
        rows = conn.execute(sa.select(t.term.c.id, t.term.c.name, t.term.c.definition, t.term.c.synonyms)
                            .where(where(t.term.c.id), t.term.c.status != "rejected"))
        return {r.id: f"{r.name}. {r.definition} Also called: {', '.join(r.synonyms)}" for r in rows}
    if kind == "measure":
        rows = conn.execute(sa.select(t.measure.c.id, t.measure.c.name, t.measure.c.description, t.measure.c.expression)
                            .where(where(t.measure.c.id), t.measure.c.status != "rejected"))
        return {r.id: f"{r.name}: {r.description} ({r.expression})" for r in rows}
    if kind == "dataset":
        cols = sa.func.string_agg(t.field.c.name, sa.literal_column("', '"))
        rows = conn.execute(sa.select(t.dataset.c.id, t.dataset.c.schema_name, t.dataset.c.name, t.dataset.c.comment, cols.label("cols"))
                            .join(t.field, t.field.c.dataset_id == t.dataset.c.id)
                            .where(where(t.dataset.c.id)).group_by(t.dataset.c.id))
        return {r.id: f"Table {r.name} ({r.schema_name}). {r.comment or ''} Columns: {r.cols}" for r in rows}
    rows = conn.execute(sa.select(t.field.c.id, t.field.c.name, t.field.c.data_type, t.field.c.role, t.field.c.comment,
                                  t.dataset.c.name.label("ds"))
                        .join(t.dataset, t.dataset.c.id == t.field.c.dataset_id).where(where(t.field.c.id)))
    return {r.id: f"{r.ds}.{r.name} ({r.data_type}, {r.role or 'unknown role'}). {r.comment or ''}" for r in rows}


def refresh(conn: sa.Connection, emb: Embedder, kinds: Iterable[str] = KINDS,
            ids: Optional[Sequence[str]] = None) -> int:
    ensure_index(conn, emb)
    changed = 0
    for kind in kinds:
        texts = _texts(conn, kind, ids)
        hashes = {i: hashlib.sha256(x.encode()).hexdigest() for i, x in texts.items()}
        have = dict(conn.execute(sa.select(t.embedding.c.object_id, t.embedding.c.text_hash)
                                 .where(t.embedding.c.object_type == kind,
                                        t.embedding.c.object_id.in_(list(texts)))).all())
        todo = [i for i in texts if have.get(i) != hashes[i]]
        for start in range(0, len(todo), 64):
            batch = todo[start:start + 64]
            vectors = emb.embed_documents([texts[i] for i in batch])
            for obj_id, vec in zip(batch, vectors):
                stmt = pg_insert(t.embedding).values(object_type=kind, object_id=obj_id, text_hash=hashes[obj_id], vector=vec)
                conn.execute(stmt.on_conflict_do_update(
                    index_elements=["object_type", "object_id"],
                    set_={"text_hash": stmt.excluded.text_hash, "vector": stmt.excluded.vector}))
            changed += len(batch)
    return changed


# ------------------------------------------------------------------ query
_NAME_SQL = {
    "term": f"""SELECT id, name, greatest(word_similarity(lower(name), :q),
                  coalesce((SELECT max(word_similarity(lower(s), :q)) FROM unnest(synonyms) s), 0)) AS score
               FROM {t.SCHEMA}.term WHERE status <> 'rejected'""",
    "measure": f"SELECT id, name, word_similarity(lower(name), :q) AS score FROM {t.SCHEMA}.measure WHERE status <> 'rejected'",
    "dataset": f"SELECT id, name, word_similarity(lower(name), :q) AS score FROM {t.SCHEMA}.dataset",
    "field": f"SELECT id, name, word_similarity(lower(name), :q) AS score FROM {t.SCHEMA}.field",
}


def _names(conn: sa.Connection, kind: str, ids: Sequence[str]) -> Dict[str, str]:
    table = {"term": t.term, "measure": t.measure, "dataset": t.dataset, "field": t.field}[kind]
    return dict(conn.execute(sa.select(table.c.id, table.c.name).where(table.c.id.in_(ids))).all()) if ids else {}


def search(conn: sa.Connection, emb: Embedder, query: str, kinds: Sequence[str] = KINDS, k: int = 10) -> List[Hit]:
    ensure_index(conn, emb)
    qv = emb.embed_query(query)
    dist = t.embedding.c.vector.cosine_distance(qv)
    vec_rows = conn.execute(
        sa.select(t.embedding.c.object_type, t.embedding.c.object_id, (1 - dist).label("sim"))
        .where(t.embedding.c.object_type.in_(kinds)).order_by(dist).limit(k * 3)
    ).all()

    fused: Dict[tuple, Hit] = {}
    for rank, r in enumerate(vec_rows):
        h = fused.setdefault((r.object_type, r.object_id), Hit(r.object_type, r.object_id, "", 0.0))
        h.similarity = float(r.sim)
        h.score += 1.0 / (_RRF_K + rank)

    q = query.lower()
    for kind in kinds:
        rows = conn.execute(sa.text(f"SELECT * FROM ({_NAME_SQL[kind]}) x WHERE score > 0.3 ORDER BY score DESC LIMIT :k"),
                            {"q": q, "k": k}).all()
        for rank, r in enumerate(rows):
            h = fused.setdefault((kind, r.id), Hit(kind, r.id, r.name, 0.0))
            h.name, h.name_match = r.name, float(r.score)
            h.score += 1.0 / (_RRF_K + rank)

    for kind in kinds:
        missing = [h.id for (kk, _), h in fused.items() if kk == kind and not h.name]
        for obj_id, name in _names(conn, kind, missing).items():
            fused[(kind, obj_id)].name = name

    hits = sorted(fused.values(), key=lambda h: h.score, reverse=True)[: k * 2]
    order = rerank(query, [f"{h.kind}: {h.name}" for h in hits], top_n=k)
    if order and any(score for _, score in order):
        hits = [hits[i] for i, _ in order]
    return hits[:k]
