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

Each call runs in the lower of ``VERITASGRAPH_MCP_MODE`` and the caller's role
(viewer → read, editor → write, admin → admin): a viewer token sees and can call
only read tools, here and through ``/mcp/rpc``.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query, Request

from studio_api.security import caller_actor, caller_role
from veritasgraph_mcp import __version__ as _MCP_VERSION
from veritasgraph_mcp.server import VeritasGraphMCPServer
from veritasgraph_mcp.tools import (
    RESOURCE_DEFINITIONS,
    ROLE_MODE,
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    TOOL_MODES,
    call_context,
    effective_mode,
    handle_resource_read,
    public_tools,
    tool_allowed,
)

mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])

# A stdio-free server instance, reused only for its JSON-RPC dispatch logic.
_bridge = VeritasGraphMCPServer()

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


def _mode(request: Request) -> str:
    return effective_mode(ROLE_MODE.get(caller_role(request), "read"))


@mcp_router.get("/")
async def mcp_info(request: Request) -> dict:
    """Server identity, capabilities, and a summary of what is exposed."""
    mode = _mode(request)
    return {
        "server": "veritasgraph-mcp",
        "version": _MCP_VERSION,
        "protocolVersion": "2024-11-05",
        "transport": "http-bridge",
        "capabilities": {"tools": {}, "resources": {}},
        "mode": mode,
        "tool_count": len(public_tools(mode)),
        "resource_count": len(RESOURCE_DEFINITIONS),
        "rpc_endpoint": "/mcp/rpc",
    }


@mcp_router.get("/tools")
async def list_tools(request: Request) -> dict:
    return {"tools": public_tools(_mode(request))}


@mcp_router.get("/resources")
async def list_resources() -> dict:
    return {"resources": RESOURCE_DEFINITIONS}


@mcp_router.get("/resources/read")
async def read_resource(
    request: Request, uri: str = Query(..., description="veritasgraph:// resource URI")
):
    def _read() -> Dict[str, Any]:
        with call_context(_mode(request), caller_actor(request)):
            return handle_resource_read(uri)

    return await asyncio.to_thread(_read)


@mcp_router.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str, request: Request, body: Dict[str, Any] = Body(default_factory=dict)
) -> dict:
    """Invoke a single MCP tool and return its raw result payload."""
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"Unknown MCP tool: {tool_name}")
    mode = _mode(request)
    if not tool_allowed(tool_name, mode):
        raise HTTPException(
            status_code=403,
            detail=f"MCP tool {tool_name} needs '{TOOL_MODES[tool_name]}' mode; this caller has '{mode}'.",
        )
    args = _coerce_arguments(tool_name, body or {})
    actor = caller_actor(request)

    def _call() -> dict:
        with call_context(mode, actor):
            return handler(args)

    return await asyncio.to_thread(_call)


@mcp_router.post("/rpc")
async def json_rpc(request: Request, payload: Dict[str, Any] = Body(...)):
    """Full JSON-RPC 2.0 bridge — dispatch any MCP method over HTTP."""
    response = await asyncio.to_thread(
        _bridge.dispatch, payload, mode=_mode(request), actor=caller_actor(request)
    )
    # Notifications (no id) produce no response body.
    return response if response is not None else {"jsonrpc": "2.0", "result": None}
