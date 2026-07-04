"""MCP bridge — expose the VeritasGraph MCP server through Studio over HTTP.

The VeritasGraph MCP server (:mod:`veritasgraph_mcp`) normally speaks JSON-RPC
2.0 over stdio so IDEs can drive it. This router mounts the *same* tool and
resource handlers over HTTP so that:

* the Studio orchestrator can invoke the MCP tools as ordinary loopback tools
  (they are seeded into the ``tools`` section pointing at ``/mcp/tools/{name}``),
* the Studio UI can list and try the MCP tools, and
* HTTP-based MCP clients can talk to the server via a single ``/mcp/rpc`` JSON-RPC
  endpoint.

Every handler touches the shared GraphRAG engine, so the work runs in a worker
thread (mirroring the graphrag router) to keep the event loop responsive.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query

from veritasgraph_mcp import __version__ as _MCP_VERSION
from veritasgraph_mcp.server import VeritasGraphMCPServer
from veritasgraph_mcp.tools import (
    RESOURCE_DEFINITIONS,
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    handle_resource_read,
)

mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])

# A stdio-free server instance, reused only for its JSON-RPC dispatch logic.
_bridge = VeritasGraphMCPServer()

# The public (handler-free) view of each tool definition.
_PUBLIC_TOOLS = [
    {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
    for t in TOOL_DEFINITIONS
]

# First required argument for each tool, used to map a generic ``query`` field
# (posted by the orchestrator's tool loop) onto the tool's real input.
_PRIMARY_ARG = {
    t["name"]: (t.get("inputSchema", {}).get("required") or [None])[0]
    for t in TOOL_DEFINITIONS
}


def _coerce_arguments(tool_name: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Turn an HTTP request body into MCP tool arguments.

    Accepts either an MCP-style ``{"arguments": {...}}`` envelope or a flat dict.
    A generic ``query`` field is mapped onto the tool's first required argument
    so the Studio orchestrator's uniform ``{"query": ...}`` payload just works.
    """
    if isinstance(body.get("arguments"), dict):
        args = dict(body["arguments"])
    else:
        args = {k: v for k, v in body.items() if k != "arguments"}

    primary = _PRIMARY_ARG.get(tool_name)
    if primary and primary not in args and "query" in args:
        args[primary] = args["query"]
    return args


@mcp_router.get("/")
async def mcp_info() -> dict:
    """Server identity, capabilities, and a summary of what is exposed."""
    return {
        "server": "veritasgraph-mcp",
        "version": _MCP_VERSION,
        "protocolVersion": "2024-11-05",
        "transport": "http-bridge",
        "capabilities": {"tools": {}, "resources": {}},
        "tool_count": len(_PUBLIC_TOOLS),
        "resource_count": len(RESOURCE_DEFINITIONS),
        "rpc_endpoint": "/mcp/rpc",
    }


@mcp_router.get("/tools")
async def list_tools() -> dict:
    return {"tools": _PUBLIC_TOOLS}


@mcp_router.get("/resources")
async def list_resources() -> dict:
    return {"resources": RESOURCE_DEFINITIONS}


@mcp_router.get("/resources/read")
async def read_resource(uri: str = Query(..., description="veritasgraph:// resource URI")):
    resource = await asyncio.to_thread(handle_resource_read, uri)
    return resource


@mcp_router.post("/tools/{tool_name}")
async def call_tool(tool_name: str, body: Dict[str, Any] = Body(default_factory=dict)) -> dict:
    """Invoke a single MCP tool and return its raw result payload."""
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"Unknown MCP tool: {tool_name}")
    args = _coerce_arguments(tool_name, body or {})
    result = await asyncio.to_thread(handler, args)
    return result


@mcp_router.post("/rpc")
async def json_rpc(request: Dict[str, Any] = Body(...)):
    """Full JSON-RPC 2.0 bridge — dispatch any MCP method over HTTP."""
    response = await asyncio.to_thread(_bridge.dispatch, request)
    # Notifications (no id) produce no response body.
    return response if response is not None else {"jsonrpc": "2.0", "result": None}
