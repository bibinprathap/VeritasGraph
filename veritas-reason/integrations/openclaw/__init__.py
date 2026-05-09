"""
VeritasReason × OpenClaw Integration
==================================

First-class integration between the VeritasReason semantic intelligence stack and
`OpenClaw <https://openclaw.ai>`_ — the open-source personal AI agent platform.

OpenClaw connects to external tools via MCP (Model Context Protocol).  This
integration exposes the full VeritasReason MCP surface (12 tools, 3 resources) to
any OpenClaw agent and also ships a lightweight ``OpenClawKGTool`` that can be
dropped directly into an OpenClaw SOUL.md tool-list as a native tool.

Public surface
--------------
OpenClawKGTool      — Thin wrapper around the VeritasReason REST API usable as an
                       OpenClaw native tool (no MCP gateway required)
OpenClawMCPConfig   — Helper that emits the ``mcporter.json`` snippet needed to
                       wire VeritasReason's MCP server into an OpenClaw gateway

Quick start
-----------
    pip install veritas-reason

    >>> from integrations.openclaw import OpenClawKGTool, OpenClawMCPConfig
    >>> print(OpenClawMCPConfig().to_json())   # paste into mcporter.json
    >>> tool = OpenClawKGTool(base_url="http://localhost:8000")
    >>> result = tool.extract("OpenClaw is an open-source AI agent framework.")

MCP quick start
---------------
Run the VeritasReason MCP server once::

    python -m veritasreason.mcp_server

Then add the printed config snippet to your OpenClaw ``mcporter.json`` and
restart the OpenClaw Gateway::

    openclaw gateway restart

All 12 VeritasReason tools are then available as native OpenClaw agent tools.

Compatibility
-------------
Requires ``veritasreason >= 0.3.0``.  The MCP path requires ``python >= 3.8`` and
a running ``veritasreason.mcp_server`` instance.  The REST path requires a running
``veritasreason.server`` instance (``python -m veritasreason.server``, port 8000 by
default).
"""

from .mcp_tool import OpenClawKGTool, OpenClawMCPConfig

__all__ = [
    "OpenClawKGTool",
    "OpenClawMCPConfig",
]

__version__ = "0.1.0"
