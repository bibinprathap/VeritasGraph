"""Tool-specific controllers: probe/test a registered tool against its real endpoint.

The collection CRUD (create/read/update/delete) for tools is handled by the
generic :mod:`studio_api.controllers.resources` factory. This module adds the
one tool-specific action the generic surface can't express: actually *calling*
the tool's configured endpoint so an operator can validate a real external tool
before exposing it to agents.

Security: outbound probes are guarded against the most dangerous SSRF target —
the cloud metadata / link-local range (169.254.0.0/16) — while still allowing
loopback, private (on-prem/enterprise), and public endpoints, since enterprise
tools legitimately live on internal networks.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from typing import Any, Dict, Optional
from urllib import parse as urlparse

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from studio_api.models import ResourceUpdateRequest, Section
from studio_api.store import StudioStore

# Cap how much of a tool response we read back into the validation panel.
_MAX_SAMPLE_BYTES = 2048
_DEFAULT_TIMEOUT = 8.0


class ToolProbeError(Exception):
    """Raised when a tool endpoint is unsafe or unreachable."""


def _assert_safe_url(endpoint: str) -> str:
    """Validate scheme/host and block link-local (cloud metadata) targets."""
    parsed = urlparse.urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ToolProbeError("Endpoint must be an http:// or https:// URL.")
    host = parsed.hostname
    if not host:
        raise ToolProbeError("Endpoint is missing a host.")

    # Resolve every address the host maps to and reject link-local / metadata.
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ToolProbeError(f"Cannot resolve host '{host}': {exc}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise ToolProbeError(
                f"Refusing to call blocked address {ip} (link-local/metadata range)."
            )
    return endpoint


def _probe(endpoint: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Perform a real HTTP request to the tool endpoint and summarise the result."""
    _assert_safe_url(endpoint)

    method = str(config.get("method") or "").upper() or "POST"
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
        method = "POST"
    timeout = float(config.get("timeout_seconds") or _DEFAULT_TIMEOUT)

    headers: Dict[str, str] = {"Accept": "application/json"}
    extra = config.get("headers")
    if isinstance(extra, dict):
        headers.update({str(k): str(v) for k, v in extra.items()})
    auth_header = str(config.get("auth_header") or "").strip()
    if auth_header and ":" in auth_header:
        name, _, value = auth_header.partition(":")
        headers[name.strip()] = value.strip()

    sample = str(config.get("test_payload") or "").strip()
    json_body: Optional[Dict[str, Any]] = None
    if method in {"POST", "PUT", "PATCH"}:
        if sample:
            try:
                json_body = json.loads(sample)
            except json.JSONDecodeError:
                json_body = {"query": sample}
        else:
            json_body = {"query": "ping", "source": "veritasgraph-studio"}

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            resp = client.request(method, endpoint, headers=headers, json=json_body)
    except httpx.HTTPError as exc:
        raise ToolProbeError(f"Request failed: {exc}") from exc

    latency_ms = round((time.perf_counter() - started) * 1000)
    body = resp.text[:_MAX_SAMPLE_BYTES]
    # MCP HTTP proxies can legitimately return 400 "No sessionId" on direct
    # probe requests (no initialized MCP stream/session yet). Treat that as
    # "reachable and ready" so operators can mark the connector as healthy.
    body_lc = body.lower()
    mcp_pre_session = (
        resp.status_code == 400
        and (
            "no sessionid" in body_lc
            or "no valid session id" in body_lc
            or "session id" in body_lc
        )
        and (
            "mcp" in endpoint.lower()
            or str(config.get("mcp_command") or "").strip() != ""
        )
    )

    # Graphrag endpoint requires a richer payload than the generic probe. A
    # 422 "Field required" still proves the local service is alive.
    graphrag_reachable = (
        "/graphrag/query" in endpoint.lower()
        and resp.status_code == 422
        and "field required" in body_lc
    )

    ok = resp.is_success or mcp_pre_session or graphrag_reachable
    return {
        "ok": ok,
        "status_code": resp.status_code,
        "latency_ms": latency_ms,
        "content_type": resp.headers.get("content-type", ""),
        "sample": body,
        "method": method,
    }


async def test_tool(store: StudioStore, tool_id: str) -> JSONResponse:
    """Probe a tool's endpoint and update its connected/disabled status."""
    section = Section.TOOLS.value
    record = await asyncio.to_thread(store.get_resource, section, tool_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    endpoint = str((record.config or {}).get("endpoint") or "").strip()
    if not endpoint:
        raise HTTPException(status_code=400, detail="Tool has no endpoint to test.")

    try:
        result = await asyncio.to_thread(_probe, endpoint, dict(record.config or {}))
    except ToolProbeError as exc:
        # Reachability failure -> mark disabled so the UI reflects reality.
        await asyncio.to_thread(
            store.update_resource, section, tool_id, ResourceUpdateRequest(status="disabled")
        )
        return JSONResponse(
            status_code=200,
            content={
                "message": "Tool validation failed",
                "id": tool_id,
                "ok": False,
                "status": "disabled",
                "detail": str(exc),
            },
        )

    new_status = "connected" if result["ok"] else "disabled"
    updated = await asyncio.to_thread(
        store.update_resource, section, tool_id, ResourceUpdateRequest(status=new_status)
    )
    return JSONResponse(
        content={
            "message": "Tool validated",
            "id": tool_id,
            "status": new_status,
            **result,
            "item": updated.model_dump(mode="json") if updated else None,
        }
    )
