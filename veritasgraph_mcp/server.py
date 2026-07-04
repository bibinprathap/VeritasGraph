"""VeritasGraph MCP Server — JSON-RPC 2.0 over stdio.

Implements the Model Context Protocol so any MCP-compatible AI tool
(Claude Desktop, Cursor, VS Code, Windsurf, Cline, Continue) can drive the
VeritasGraph knowledge-graph engine locally, with zero external data egress.

Run:
    python -m veritasgraph_mcp            # via __main__.py
    python -m veritasgraph_mcp.server     # direct
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure the repository root is importable so ``studio_api`` resolves when the
# server is launched from an arbitrary working directory (e.g. by an IDE).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from veritasgraph_mcp import __version__
from veritasgraph_mcp.tools import (
    RESOURCE_DEFINITIONS,
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    handle_resource_read,
)

log = logging.getLogger("veritasgraph.mcp.server")

# JSON-RPC error codes
_PARSE_ERROR = -32700
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603


# --------------------------------------------------------------------------- #
# Response helpers
# --------------------------------------------------------------------------- #
def _ok(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str, data: Any = None) -> dict:
    error: dict = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


# --------------------------------------------------------------------------- #
# Method handlers
# --------------------------------------------------------------------------- #
def _handle_initialize(req_id: Any, _params: dict) -> dict:
    return _ok(req_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}, "resources": {}},
        "serverInfo": {"name": "veritasgraph-mcp", "version": __version__},
    })


def _handle_tools_list(req_id: Any, _params: dict) -> dict:
    tools = [
        {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
        for t in TOOL_DEFINITIONS
    ]
    return _ok(req_id, {"tools": tools})


def _handle_tools_call(req_id: Any, params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments", {}) or {}

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return _err(req_id, _METHOD_NOT_FOUND, f"Unknown tool: {name}")

    try:
        result = handler(args)
    except Exception as exc:  # noqa: BLE001
        log.exception("Tool %s raised", name)
        return _err(req_id, _INTERNAL_ERROR, str(exc))

    return _ok(req_id, {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
        "isError": isinstance(result, dict) and "error" in result,
    })


def _handle_resources_list(req_id: Any, _params: dict) -> dict:
    return _ok(req_id, {"resources": RESOURCE_DEFINITIONS})


def _handle_resources_read(req_id: Any, params: dict) -> dict:
    uri = (params.get("uri") or "").strip()
    if not uri:
        return _err(req_id, _INVALID_PARAMS, "uri is required")
    resource = handle_resource_read(uri)
    return _ok(req_id, {
        "contents": [{
            "uri": resource["uri"],
            "mimeType": resource.get("mimeType", "application/json"),
            "text": resource.get("text", ""),
        }]
    })


def _handle_ping(req_id: Any, _params: dict) -> dict:
    return _ok(req_id, {})


_DISPATCH = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
    "resources/list": _handle_resources_list,
    "resources/read": _handle_resources_read,
    "ping": _handle_ping,
}


# --------------------------------------------------------------------------- #
# Server
# --------------------------------------------------------------------------- #
class VeritasGraphMCPServer:
    """Reads JSON-RPC requests from stdin, writes responses to stdout."""

    def __init__(self, *, debug: bool = False) -> None:
        level = logging.DEBUG if debug else logging.WARNING
        logging.basicConfig(
            stream=sys.stderr, level=level,
            format="%(name)s %(levelname)s %(message)s",
        )

    def dispatch(self, request: dict) -> Optional[dict]:
        req_id = request.get("id")  # None for notifications
        method = request.get("method", "")
        params = request.get("params") or {}

        handler = _DISPATCH.get(method)
        if handler is None:
            if req_id is None:
                return None  # unknown notification — ignore silently
            return _err(req_id, _METHOD_NOT_FOUND, f"Method not found: {method}")

        try:
            return handler(req_id, params)
        except Exception as exc:  # noqa: BLE001
            log.exception("Unhandled error in %s", method)
            if req_id is None:
                return None
            return _err(req_id, _INTERNAL_ERROR, str(exc))

    def run(self) -> None:
        log.info("VeritasGraph MCP server starting (stdio)")
        for raw_line in sys.stdin:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                request = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                _write(_err(None, _PARSE_ERROR, f"Parse error: {exc}"))
                continue

            if isinstance(request, list):  # batch
                responses = [r for r in (self.dispatch(x) for x in request) if r is not None]
                if responses:
                    _write(responses)
            else:
                resp = self.dispatch(request)
                if resp is not None:
                    _write(resp)


def _write(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="VeritasGraph MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    VeritasGraphMCPServer(debug=args.debug).run()


if __name__ == "__main__":
    main()
