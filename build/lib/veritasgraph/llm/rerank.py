"""Optional reranking. Every caller must work with mode ``none``."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Tuple

from veritasgraph.llm.client import LLMError, _Http
from veritasgraph.llm.config import endpoint, rerank_mode

Ranked = List[Tuple[int, float]]  # (index into docs, score), best first


@lru_cache(maxsize=1)
def _http() -> _Http:
    return _Http(endpoint("rerank"))


@lru_cache(maxsize=1)
def _cross_encoder():
    from sentence_transformers import CrossEncoder  # extra: rerank-local

    return CrossEncoder(endpoint("rerank").model)


def rerank(query: str, docs: List[str], top_n: int) -> Ranked:
    mode = rerank_mode()
    if not docs:
        return []
    if mode == "none":
        return [(i, 0.0) for i in range(min(top_n, len(docs)))]
    if mode == "local":
        scores = _cross_encoder().predict([(query, d) for d in docs])
        ranked = sorted(enumerate(map(float, scores)), key=lambda x: x[1], reverse=True)
        return ranked[:top_n]
    http = _http()
    if mode == "rerank-api":  # vLLM / llama.cpp / Jina-style
        resp = http.post("/rerank", {"model": http.ep.model, "query": query, "documents": docs, "top_n": top_n})
        if resp.status_code >= 400:
            raise LLMError(f"rerank rejected ({resp.status_code})", resp.status_code)
        results = resp.json()["results"]
        return [(r["index"], float(r["relevance_score"])) for r in results][:top_n]
    # tei
    resp = http.post("/rerank", {"query": query, "texts": docs})
    if resp.status_code >= 400:
        raise LLMError(f"rerank rejected ({resp.status_code})", resp.status_code)
    ranked = sorted(((r["index"], float(r["score"])) for r in resp.json()), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]
