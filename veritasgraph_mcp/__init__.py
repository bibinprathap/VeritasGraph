"""VeritasGraph MCP Server.

The first zero-trust, air-gapped GraphRAG server for the Model Context
Protocol (MCP). It exposes VeritasGraph's local knowledge-graph engine —
document ingestion, multi-hop graph-grounded querying with verifiable
citations, entity search, and graph inspection — to any MCP-compatible IDE
agent (Claude Desktop, Cursor, VS Code, Windsurf, Cline, Continue).

The server speaks JSON-RPC 2.0 over stdio and has **zero external
dependencies** beyond the VeritasGraph runtime itself, so it runs fully
offline inside air-gapped enterprise environments with no data egress.

Run:
    python -m veritasgraph_mcp            # via __main__.py
    python -m veritasgraph_mcp.server     # direct
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.1"
