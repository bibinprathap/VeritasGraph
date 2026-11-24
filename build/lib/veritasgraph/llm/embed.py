"""Embeddings over ``/v1/embeddings`` with per-model query/document prefixes."""

from __future__ import annotations

from functools import cached_property
from typing import Dict, List, Optional

import httpx

from veritasgraph.llm.client import LLMError, _Http
from veritasgraph.llm.config import Endpoint, embed_prefixes, endpoint

BATCH = 64


class Embedder(_Http):
    def __init__(self, ep: Optional[Endpoint] = None, transport: Optional[httpx.BaseTransport] = None) -> None:
        super().__init__(ep or endpoint("embed"), transport)
        self.query_prefix, self.doc_prefix = embed_prefixes(self.ep.model)

    def _embed(self, inputs: List[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for i in range(0, len(inputs), BATCH):
            batch = inputs[i : i + BATCH]
            resp = self.post("/embeddings", {"model": self.ep.model, "input": batch})
            if resp.status_code >= 400:
                raise LLMError(f"embedding request rejected ({resp.status_code})", resp.status_code)
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
        return out

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed([self.doc_prefix + t for t in texts]) if texts else []

    def embed_query(self, text: str) -> List[float]:
        return self._embed([self.query_prefix + text])[0]

    @cached_property
    def dim(self) -> int:
        return len(self._embed([self.doc_prefix + "dimension probe"])[0])

    def signature(self) -> Dict[str, object]:
        return {"model": self.ep.model, "dim": self.dim, "query_prefix": self.query_prefix, "doc_prefix": self.doc_prefix}
