#!/usr/bin/env python3
"""Seed a practical tool catalog and sample explorer agents for Studio.

This script is idempotent. It ensures a broad, general-purpose tools list exists
in the Studio Tools section, then creates sample agents wired to those tools.

Run:

    python3 demos/agent-studio/sample_tools_explorer.py
    python3 demos/agent-studio/sample_tools_explorer.py --base http://127.0.0.1:8200
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

TOOLS = [
    ("Graph Retriever", "retrieval", "http://127.0.0.1:8200/graphrag/query", "Graph-aware retrieval over indexed knowledge."),
    ("Web Search", "search", "https://api.example.local/web-search", "External web lookup for fresh context."),
    ("Code Runner", "execution", "https://api.example.local/code-runner", "Sandboxed code execution for deterministic snippets."),
    ("Slack Connector", "communication", "https://api.example.local/slack", "Post updates and fetch channel context."),
    ("Teams Connector", "communication", "https://api.example.local/teams", "Send and read Microsoft Teams messages."),
    ("Email Assistant", "email", "https://api.example.local/email", "Compose, classify, and route email actions."),
    ("Docs Workspace", "document", "https://api.example.local/docs", "Create and edit long-form docs."),
    ("Sheets Analyst", "spreadsheet", "https://api.example.local/sheets", "Tabular analysis and formula generation."),
    ("Slides Builder", "presentation", "https://api.example.local/slides", "Generate decks from structured outlines."),
    ("Cloud Drive", "storage", "https://api.example.local/drive", "Search, upload, and share workspace files."),
    ("Task Planner", "project", "https://api.example.local/tasks", "Track tasks across boards and sprints."),
    ("Design Board", "design", "https://api.example.local/design", "Draft UI/artwork concepts and review states."),
    ("GitHub Repo", "development", "https://api.example.local/github", "Read issues, PRs, and repository metadata."),
    ("Postman API Runner", "development", "https://api.example.local/postman", "Execute and validate API collections."),
    ("Power BI Connector", "bi", "https://api.example.local/powerbi", "Publish metrics to Power BI dashboards."),
    ("Tableau Connector", "bi", "https://api.example.local/tableau", "Sync curated datasets into Tableau workbooks."),
    ("AI Assistant Bridge", "ai", "https://api.example.local/ai-bridge", "Route requests to approved assistant providers."),
]

AGENTS = [
    {
        "name": "General Tools Explorer",
        "kind": "qwen3:latest",
        "description": "Sample explorer agent wired to the full general-purpose toolset.",
        "config": {
            "tags": "sample, explorer, tools",
            "prompt": "Select the best tool for each task and explain tool choice briefly.",
            "use_graph": True,
            "use_tools": True,
            "use_memory": True,
            "use_guardrails": True,
            "use_data": True,
            "context_budget": 800,
            "tool_profile": [
                "Graph Retriever",
                "Web Search",
                "Email Assistant",
                "Docs Workspace",
                "Sheets Analyst",
                "Task Planner",
                "GitHub Repo",
            ],
        },
    },
    {
        "name": "Data & BI Explorer",
        "kind": "qwen3:latest",
        "description": "Sample explorer agent focused on data, dashboarding, and reporting.",
        "config": {
            "tags": "sample, explorer, data",
            "prompt": "Use tabular tools first, then produce concise KPI summaries.",
            "use_graph": True,
            "use_tools": True,
            "use_memory": True,
            "use_guardrails": True,
            "use_data": True,
            "context_budget": 750,
            "tool_profile": [
                "Sheets Analyst",
                "Power BI Connector",
                "Tableau Connector",
                "Cloud Drive",
            ],
        },
    },
    {
        "name": "Engineering Explorer",
        "kind": "qwen3:latest",
        "description": "Sample explorer agent for software delivery and API operations.",
        "config": {
            "tags": "sample, explorer, engineering",
            "prompt": "Prefer repo and API tools; summarize findings with actionable next steps.",
            "use_graph": True,
            "use_tools": True,
            "use_memory": True,
            "use_guardrails": True,
            "use_data": True,
            "context_budget": 700,
            "tool_profile": [
                "GitHub Repo",
                "Postman API Runner",
                "Code Runner",
                "Web Search",
            ],
        },
    },
]


def _call(base: str, method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{base}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"[HTTP {exc.code}] {method} {path}\n{body}", file=sys.stderr)
        raise


def _ensure_tools(base: str) -> tuple[int, int]:
    existing = _call(base, "GET", "/tools/").get("items", [])
    by_name = {t.get("name"): t for t in existing}
    created = 0
    for name, kind, endpoint, description in TOOLS:
        if name in by_name:
            continue
        status = "disabled" if name == "Code Runner" else "connected"
        _call(
            base,
            "POST",
            "/tools/",
            {
                "name": name,
                "kind": kind,
                "status": status,
                "description": description,
                "config": {"endpoint": endpoint},
            },
        )
        created += 1
    total = _call(base, "GET", "/tools/").get("count", 0)
    return created, total


def _ensure_agents(base: str, default_model: str) -> tuple[int, int]:
    items = _call(base, "GET", "/agents/").get("items", [])
    existing_names = {a.get("name") for a in items}
    created = 0
    for agent in AGENTS:
        if agent["name"] in existing_names:
            continue
        payload = dict(agent)
        payload["kind"] = default_model
        _call(base, "POST", "/agents/", payload)
        created += 1
    total = _call(base, "GET", "/agents/").get("count", 0)
    return created, total


def _pick_model(base: str) -> str:
    models = _call(base, "GET", "/models/").get("items", [])
    if not models:
        return "qwen3:latest"
    return models[0]["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8200")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    model = _pick_model(base)
    tools_created, tools_total = _ensure_tools(base)
    agents_created, agents_total = _ensure_agents(base, model)

    kpis = _call(base, "GET", "/workspace/kpis").get("kpis", {})

    print("Studio sample explorer setup complete")
    print(f"  Tools created: {tools_created} (total: {tools_total})")
    print(f"  Agents created: {agents_created} (total: {agents_total})")
    print(
        "  KPIs: "
        f"active_agents={kpis.get('active_agents')} "
        f"tools_connected={kpis.get('tools_connected')} "
        f"eval_pass_rate={kpis.get('eval_pass_rate')} "
        f"guardrail_blocks={kpis.get('guardrail_blocks')}"
    )
    print(f"  Open: {base}/studio")


if __name__ == "__main__":
    main()
