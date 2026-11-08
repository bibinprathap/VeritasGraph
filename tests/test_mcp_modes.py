"""The stdio MCP server honours ``VERITASGRAPH_MCP_MODE`` end to end."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _session(tmp_path: Path, mode: str) -> list:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "veritasgraph_ingest_document", "arguments": {"text": "x"}},
        },
    ]
    env = {**os.environ, "VERITASGRAPH_MCP_MODE": mode, "STUDIO_DATA_DIR": str(tmp_path)}
    env.pop("VERITASGRAPH_DB", None)
    proc = subprocess.run(
        [sys.executable, "-m", "veritasgraph_mcp"],
        input="\n".join(json.dumps(r) for r in requests) + "\n",
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=60,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_read_mode_hides_and_rejects_write_tools(tmp_path):
    init, listing, call = _session(tmp_path, "read")
    assert init["result"]["instructions"]
    names = {t["name"] for t in listing["result"]["tools"]}
    assert "veritasgraph_query" in names
    assert "veritasgraph_ingest_document" not in names
    assert "veritasgraph_clear_graph" not in names
    assert call["error"]["code"] == -32601


def test_write_mode_exposes_ingest_but_not_admin_tools(tmp_path):
    _, listing, _ = _session(tmp_path, "write")
    names = {t["name"] for t in listing["result"]["tools"]}
    assert "veritasgraph_ingest_document" in names
    assert "veritasgraph_clear_graph" not in names
