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

from veritasgraph_mcp import __version__  # noqa: E402
from veritasgraph_mcp.tools import (  # noqa: E402
    RESOURCE_DEFINITIONS,
    SERVER_INSTRUCTIONS,
    TOOL_HANDLERS,
    call_context,
    current_mode,
    effective_mode,
    handle_resource_read,
    public_prompts,
    public_tools,
    render_prompt,
    tool_allowed,
)

log = logging.getLogger("veritasgraph.mcp.server")

# Newest first; the first entry is offered when a client asks for a version we
# do not know.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

ICON_URL = "https://raw.githubusercontent.com/bibinprathap/VeritasGraph/restored-main/assets/veritasgraph-logo.png"

SERVER_INFO = {
    "name": "veritasgraph-mcp",
    "title": "VeritasGraph",
    "version": __version__,
    "websiteUrl": "https://bibinprathap.github.io/VeritasGraph/",
    "icons": [{"src": ICON_URL, "mimeType": "image/png", "sizes": ["512x512"]}],
}

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
def _handle_initialize(req_id: Any, params: dict) -> dict:
    requested = params.get("protocolVersion")
    version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
    return _ok(req_id, {
        "protocolVersion": version,
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"listChanged": False, "subscribe": False},
            "prompts": {"listChanged": False},
        },
        "serverInfo": SERVER_INFO,
        "instructions": SERVER_INSTRUCTIONS,
    })


def _handle_tools_list(req_id: Any, _params: dict) -> dict:
    return _ok(req_id, {"tools": public_tools(current_mode())})


def _tool_result(result: Any, is_error: bool) -> dict:
    out: dict = {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
        "isError": is_error,
    }
    if isinstance(result, dict):
        out["structuredContent"] = result
    return out


def _handle_tools_call(req_id: Any, params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments") or {}

    handler = TOOL_HANDLERS.get(name)
    # A tool above the current mode is reported exactly like an unknown one.
    if handler is None or not tool_allowed(name):
        return _err(req_id, _METHOD_NOT_FOUND, f"Unknown tool: {name}")
    if not isinstance(args, dict):
        return _err(req_id, _INVALID_PARAMS, "arguments must be an object")

    try:
        result = handler(args)
    except Exception as exc:  # noqa: BLE001 - tool failures are results, not protocol errors
        log.exception("Tool %s raised", name)
        return _ok(req_id, _tool_result({"error": f"{type(exc).__name__}: {exc}"}, True))

    return _ok(req_id, _tool_result(result, isinstance(result, dict) and "error" in result))


def _handle_prompts_list(req_id: Any, _params: dict) -> dict:
    return _ok(req_id, {"prompts": public_prompts()})


def _handle_prompts_get(req_id: Any, params: dict) -> dict:
    name = params.get("name", "")
    try:
        return _ok(req_id, render_prompt(name, params.get("arguments") or {}))
    except KeyError:
        return _err(req_id, _INVALID_PARAMS, f"Unknown prompt: {name}")
    except ValueError as exc:
        return _err(req_id, _INVALID_PARAMS, str(exc))


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
    "prompts/list": _handle_prompts_list,
    "prompts/get": _handle_prompts_get,
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

    def dispatch(
        self, request: dict, *, mode: Optional[str] = None, actor: str = "mcp:stdio"
    ) -> Optional[dict]:
        """Handle one JSON-RPC request as ``mode`` (capped by VERITASGRAPH_MCP_MODE)."""
        with call_context(effective_mode(mode), actor):
            return self._dispatch(request)

    def _dispatch(self, request: dict) -> Optional[dict]:
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
    import os

    parser = argparse.ArgumentParser(description="VeritasGraph MCP Server")
    parser.add_argument("--version", action="version", version=f"veritasgraph-mcp {__version__}")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--transport", choices=("stdio", "http"),
        default=os.getenv("VERITASGRAPH_MCP_TRANSPORT", "stdio"),
        help="stdio (default) or Streamable HTTP",
    )
    parser.add_argument("--host", default=os.getenv("VERITASGRAPH_MCP_HOST", "127.0.0.1"),
                        help="HTTP bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.getenv("VERITASGRAPH_MCP_PORT", "8765")),
                        help="HTTP port (default 8765)")
    parser.add_argument("--path", default="/mcp", help="HTTP endpoint path (default /mcp)")
    args = parser.parse_args()
    # Installed copies (pip/uvx/MCPB) would otherwise keep the graph inside the
    # package directory, which uvx may discard; use ~/.veritasgraph instead.
    if not (os.getenv("STUDIO_DATA_DIR") or os.getenv("VERITASGRAPH_DB") or (_REPO_ROOT / ".git").exists()):
        os.environ["STUDIO_DATA_DIR"] = str(Path.home() / ".veritasgraph")
    server = VeritasGraphMCPServer(debug=args.debug)
    if args.transport == "http":
        from veritasgraph_mcp.http_transport import serve

        serve(server, host=args.host, port=args.port, path=args.path)
    else:
        server.run()


if __name__ == "__main__":
    main()
