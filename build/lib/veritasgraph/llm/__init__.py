"""One way to reach on-prem models: OpenAI-compatible chat, embeddings and rerank."""

from veritasgraph.llm.client import ChatClient, LLMError
from veritasgraph.llm.config import Endpoint, endpoint, embed_prefixes, rerank_mode
from veritasgraph.llm.embed import Embedder
from veritasgraph.llm.rerank import rerank
from veritasgraph.llm.structured import structured

__all__ = [
    "ChatClient",
    "Embedder",
    "Endpoint",
    "LLMError",
    "embed_prefixes",
    "endpoint",
    "rerank",
    "rerank_mode",
    "structured",
]
