"""
VeritasReason MCP Server Package

A full Model Context Protocol (MCP) server for VeritasReason — exposes knowledge graph
construction, semantic extraction, decision intelligence, reasoning, analytics,
and export capabilities as MCP tools and resources.

Run the server:
    python -m mcp.server        # from repo root
    python -m veritasreason.mcp_server  # alias inside installed package

Configure in Claude Desktop, Windsurf, Cline, Continue, VS Code:
    {
        "mcpServers": {
            "veritasreason": {
                "command": "python",
                "args": ["-m", "mcp.server"],
                "cwd": "/path/to/veritasreason"
            }
        }
    }
"""

from .server import VeritasReasonMCPServer, main

__all__ = ["VeritasReasonMCPServer", "main"]
__version__ = "0.4.0"
