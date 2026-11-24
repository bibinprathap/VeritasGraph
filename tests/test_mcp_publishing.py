"""Publishing metadata stays in sync, and the protocol features listed in the registries work."""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from veritasgraph_mcp import __version__
from veritasgraph_mcp.http_transport import make_server
from veritasgraph_mcp.server import (
    LATEST_PROTOCOL_VERSION,
    SERVER_INFO,
    VeritasGraphMCPServer,
)
from veritasgraph_mcp.tools import PROMPT_DEFINITIONS, TOOL_DEFINITIONS

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_JSON = json.loads((REPO_ROOT / "veritasgraph_mcp" / "server.json").read_text())
MANIFEST = json.loads((REPO_ROOT / "mcpb" / "manifest.json").read_text())
PYPROJECT = (REPO_ROOT / "pyproject.toml").read_text()


def _pyproject_value(key: str) -> str:
    # tomllib is 3.11+, CI also runs 3.10.
    return re.search(rf'^{key}\s*=\s*"([^"]+)"', PYPROJECT, re.MULTILINE).group(1)


def test_versions_match():
    assert _pyproject_value("version") == __version__
    assert SERVER_JSON["version"] == __version__
    assert MANIFEST["version"] == __version__
    assert SERVER_INFO["version"] == __version__
    for pkg in SERVER_JSON["packages"]:
        assert (pkg.get("version") or pkg["identifier"].rsplit(":", 1)[-1]) == __version__


def test_readme_has_registry_ownership_marker():
    readme = (REPO_ROOT / _pyproject_value("readme")).read_text()
    assert f"mcp-name: {SERVER_JSON['name']}" in readme


def test_dockerfile_has_registry_label():
    dockerfile = (REPO_ROOT / "veritasgraph_mcp" / "Dockerfile").read_text()
    assert f'io.modelcontextprotocol.server.name="{SERVER_JSON["name"]}"' in dockerfile


def test_manifest_lists_every_tool_and_prompt():
    assert [t["name"] for t in MANIFEST["tools"]] == [t["name"] for t in TOOL_DEFINITIONS]
    by_name = {p["name"]: p for p in MANIFEST["prompts"]}
    assert set(by_name) == {p["name"] for p in PROMPT_DEFINITIONS}
    for prompt in PROMPT_DEFINITIONS:
        expected = re.sub(r"\{(\w+)\}", r"${arguments.\1}", prompt["_text"])
        assert by_name[prompt["name"]]["text"] == expected
        assert by_name[prompt["name"]]["arguments"] == [a["name"] for a in prompt["arguments"]]


def test_every_tool_has_title_and_annotations():
    for tool in TOOL_DEFINITIONS:
        assert tool["title"], tool["name"]
        hints = tool["annotations"]
        assert isinstance(hints["readOnlyHint"], bool), tool["name"]
        if tool.get("_mode", "read") == "read":
            assert hints["readOnlyHint"] is True, tool["name"]
    clear = next(t for t in TOOL_DEFINITIONS if t["name"] == "veritasgraph_clear_graph")
    assert clear["annotations"]["destructiveHint"] is True


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("VERITASGRAPH_DB", raising=False)
    return VeritasGraphMCPServer()


def test_initialize_negotiates_protocol_version(server):
    def negotiated(version):
        reply = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                 "params": {"protocolVersion": version}})
        return reply["result"]["protocolVersion"]

    assert negotiated("2024-11-05") == "2024-11-05"
    assert negotiated("2025-06-18") == "2025-06-18"
    assert negotiated("1999-01-01") == LATEST_PROTOCOL_VERSION


def test_prompts(server):
    listing = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"})
    assert {p["name"] for p in listing["result"]["prompts"]} == {"grounded_answer", "verify_claim", "explore_entity"}
    assert all("_text" not in p for p in listing["result"]["prompts"])

    got = server.dispatch({"jsonrpc": "2.0", "id": 2, "method": "prompts/get",
                           "params": {"name": "grounded_answer", "arguments": {"question": "Who owns Beta?"}}})
    text = got["result"]["messages"][0]["content"]["text"]
    assert "Who owns Beta?" in text and "veritasgraph_check_answerable" in text

    missing = server.dispatch({"jsonrpc": "2.0", "id": 3, "method": "prompts/get",
                               "params": {"name": "grounded_answer", "arguments": {}}})
    assert missing["error"]["code"] == -32602
    unknown = server.dispatch({"jsonrpc": "2.0", "id": 4, "method": "prompts/get", "params": {"name": "nope"}})
    assert unknown["error"]["code"] == -32602


def test_tool_call_returns_structured_content(server):
    reply = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": "veritasgraph_check_answerable",
                                        "arguments": {"question": "Who owns Beta?"}}})
    result = reply["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_bad_arguments_are_invalid_params(server):
    reply = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": "veritasgraph_check_answerable", "arguments": "x"}})
    assert reply["error"]["code"] == -32602


@pytest.fixture()
def http_url(server, monkeypatch):
    monkeypatch.delenv("VERITASGRAPH_MCP_TOKEN", raising=False)
    monkeypatch.delenv("VERITASGRAPH_MCP_ALLOWED_ORIGINS", raising=False)
    httpd = make_server(server, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _post(url: str, body: object, headers: dict | None = None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, None


def test_http_transport(http_url, monkeypatch):
    status, body = _post(f"{http_url}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert status == 200 and body["result"]["serverInfo"]["name"] == "veritasgraph-mcp"

    status, body = _post(f"{http_url}/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert status == 202 and body is None

    status, body = _post(f"{http_url}/mcp", [{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                                             {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    assert status == 200 and [r["id"] for r in body] == [1, 2]

    assert _post(f"{http_url}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                 {"Origin": "https://evil.example"})[0] == 403
    assert _post(f"{http_url}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                 {"Origin": "http://localhost:3000"})[0] == 200

    with urllib.request.urlopen(f"{http_url}/healthz", timeout=10) as resp:
        assert resp.status == 200

    monkeypatch.setenv("VERITASGRAPH_MCP_TOKEN", "s3cret")
    assert _post(f"{http_url}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 401
    assert _post(f"{http_url}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                 {"Authorization": "Bearer s3cret"})[0] == 200
