"""Streamable HTTP transport for the VeritasGraph MCP server (stdlib only).

Clients POST JSON-RPC messages to one endpoint (default ``/mcp``) and get a
single ``application/json`` reply; the server never opens an SSE stream, so
``GET`` returns 405 as the spec allows. ``GET /healthz`` is a liveness probe.

Safety defaults:

* binds to ``127.0.0.1`` unless told otherwise;
* rejects browser ``Origin`` headers that are not loopback, or not listed in
  ``VERITASGRAPH_MCP_ALLOWED_ORIGINS`` (DNS-rebinding protection);
* requires ``Authorization: Bearer $VERITASGRAPH_MCP_TOKEN`` when that is set;
* caps request bodies at ``VERITASGRAPH_MCP_MAX_BODY`` bytes (default 10 MB).
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import urlsplit

log = logging.getLogger("veritasgraph.mcp.http")

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _allowed_origins() -> set:
    raw = os.getenv("VERITASGRAPH_MCP_ALLOWED_ORIGINS", "")
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


def origin_allowed(origin: Optional[str]) -> bool:
    if not origin:
        return True  # non-browser clients send no Origin
    origin = origin.rstrip("/")
    if origin in _allowed_origins():
        return True
    return (urlsplit(origin).hostname or "") in _LOOPBACK_HOSTS


def token_ok(header: Optional[str]) -> bool:
    expected = os.getenv("VERITASGRAPH_MCP_TOKEN", "")
    if not expected:
        return True
    scheme, _, supplied = (header or "").partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(supplied.strip(), expected)


class _Handler(BaseHTTPRequestHandler):
    server_version = "veritasgraph-mcp"
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: Any = None, headers: Optional[dict] = None) -> None:
        data = b"" if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _path(self) -> str:
        return urlsplit(self.path).path.rstrip("/") or "/"

    def _guard(self) -> bool:
        if not origin_allowed(self.headers.get("Origin")):
            self._send(403, {"error": "origin not allowed"})
            return False
        if not token_ok(self.headers.get("Authorization")):
            self._send(401, {"error": "unauthorized"}, {"WWW-Authenticate": "Bearer"})
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self._path() == "/healthz":
            self._send(200, {"status": "ok"})
        elif self._path() == self.server.mcp_path:  # type: ignore[attr-defined]
            self._send(405, {"error": "this server does not open SSE streams"}, {"Allow": "POST"})
        else:
            self._send(404, {"error": "not found"})

    def do_DELETE(self) -> None:  # noqa: N802
        self._send(405, {"error": "sessions are not used"}, {"Allow": "POST"})

    def do_POST(self) -> None:  # noqa: N802
        if self._path() != self.server.mcp_path:  # type: ignore[attr-defined]
            self._send(404, {"error": "not found"})
            return
        if not self._guard():
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length <= 0:
            self._send(400, {"error": "a JSON body with Content-Length is required"})
            return
        if length > self.server.max_body:  # type: ignore[attr-defined]
            self._send(413, {"error": "request body too large"})
            return
        try:
            message = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": f"Parse error: {exc}"}})
            return

        mcp = self.server.mcp  # type: ignore[attr-defined]
        if isinstance(message, list):
            replies = [r for r in (mcp.dispatch(m, actor="mcp:http") for m in message if isinstance(m, dict))
                       if r is not None]
            reply: Any = replies or None
        elif isinstance(message, dict):
            reply = mcp.dispatch(message, actor="mcp:http")
        else:
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32600, "message": "Invalid request"}})
            return
        # Notifications and responses get 202 Accepted with no body.
        if reply is None:
            self._send(202)
        else:
            self._send(200, reply)

    def log_message(self, fmt: str, *args: Any) -> None:
        log.debug("%s - " + fmt, self.address_string(), *args)


def make_server(mcp: Any, host: str = "127.0.0.1", port: int = 8765, path: str = "/mcp") -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.daemon_threads = True
    httpd.mcp = mcp  # type: ignore[attr-defined]
    httpd.mcp_path = "/" + path.strip("/")  # type: ignore[attr-defined]
    httpd.max_body = int(os.getenv("VERITASGRAPH_MCP_MAX_BODY", str(10 * 1024 * 1024)))  # type: ignore[attr-defined]
    return httpd


def serve(mcp: Any, host: str = "127.0.0.1", port: int = 8765, path: str = "/mcp") -> None:
    if host not in _LOOPBACK_HOSTS and not os.getenv("VERITASGRAPH_MCP_TOKEN"):
        log.warning(
            "Listening on %s without VERITASGRAPH_MCP_TOKEN: anyone who can reach this "
            "port can call the tools. Set a token or keep VERITASGRAPH_MCP_MODE=read.", host
        )
    httpd = make_server(mcp, host, port, path)
    log.warning("VeritasGraph MCP listening on http://%s:%d%s", host, port, httpd.mcp_path)  # type: ignore[attr-defined]
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
