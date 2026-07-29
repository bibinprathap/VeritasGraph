"""Vendored VeritasGraph GraphRAG engine (subset of ``studio_api``).

Only the self-contained :mod:`studio_api.graphrag_engine` is bundled here so the
municipality chatbot is fully portable and does **not** depend on an external
``veritasgraph``/``veritasgraph-mcp`` PyPI install. The engine needs nothing
beyond the standard library and ``httpx``.
"""

__all__ = ["__version__"]

__version__ = "0.1.2+vendored"
