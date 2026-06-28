"""Tests for the Agent Studio backend.

The store persists to a JSON snapshot, so each test run is isolated by pointing
``STUDIO_DATA_DIR`` at a temp directory before importing the app.
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path))
    # Make the simulation deterministic by requiring explicit /advance calls.
    monkeypatch.setenv("STUDIO_EVAL_STEP_SECONDS", "100000")
    monkeypatch.setenv("STUDIO_FT_STEP_SECONDS", "100000")

    for mod in [m for m in sys.modules if m.startswith("studio_api")]:
        del sys.modules[mod]

    from fastapi.testclient import TestClient

    main = importlib.import_module("studio_api.main")
    return TestClient(main.app)


# --------------------------------------------------------------------------- #
# Collection CRUD
# --------------------------------------------------------------------------- #
def test_seed_data_present(client):
    resp = client.get("/agents/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["section"] == "agents"
    assert body["count"] >= 1


def test_resource_crud_lifecycle(client):
    create = client.post("/tools/", json={"name": "Vector Search", "kind": "retrieval"})
    assert create.status_code == 201
    item = create.json()["item"]
    assert item["status"] == "connected"
    rid = item["id"]

    patched = client.patch(f"/tools/{rid}", json={"status": "disabled"})
    assert patched.status_code == 200
    assert patched.json()["item"]["status"] == "disabled"

    got = client.get(f"/tools/{rid}")
    assert got.json()["item"]["status"] == "disabled"

    deleted = client.delete(f"/tools/{rid}")
    assert deleted.status_code == 200
    assert client.get(f"/tools/{rid}").status_code == 404


def test_unknown_section_404(client):
    assert client.get("/nonsense/").status_code == 404


# --------------------------------------------------------------------------- #
# Local model discovery
# --------------------------------------------------------------------------- #
def test_models_endpoint_shape(client):
    resp = client.get("/models/")
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload) == {"items", "count", "source"}
    assert payload["count"] == len(payload["items"])
    assert payload["source"] in {"ollama-http", "ollama-cli", "none"}
    for model in payload["items"]:
        assert model["id"]
        assert model["name"]


def test_playground_chat_unknown_agent(client):
    resp = client.post("/playground/chat", json={"agent_id": "nope", "message": "hi"})
    assert resp.status_code == 404


def test_playground_chat_runs_against_model(client, monkeypatch):
    # Create an agent with a model and system prompt.
    created = client.post(
        "/agents/",
        json={
            "name": "Echo",
            "kind": "test-model",
            "description": "Be terse.",
            "config": {"prompt": "Be terse."},
        },
    ).json()["item"]

    captured = {}

    class _FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "pong"}, "eval_count": 3}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):  # noqa: A002 - mirror httpx signature
            captured["url"] = url
            captured["body"] = json
            return _FakeResponse()

    import studio_api.routes.playground as pg

    monkeypatch.setattr(pg.httpx, "AsyncClient", _FakeClient)

    resp = client.post(
        "/playground/chat",
        json={"agent_id": created["id"], "message": "ping"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "pong"
    assert data["model"] == "test-model"
    # The system prompt and user message were forwarded to the model.
    roles = [m["role"] for m in captured["body"]["messages"]]
    assert roles == ["system", "user"]
    assert captured["body"]["model"] == "test-model"


# --------------------------------------------------------------------------- #
# GraphRAG knowledge graph
# --------------------------------------------------------------------------- #
def _patch_graph_chat(monkeypatch):
    """Replace the engine's LLM call with a deterministic stub.

    Extraction prompts return JSON entities/relationships; answer prompts return
    a cited sentence. The two are distinguished by the system message content.
    """
    import studio_api.graphrag_engine as ge

    extraction = (
        '{"entities": ['
        '{"name": "Acme Corp", "type": "organization", "description": "A software company"},'
        '{"name": "Jane Doe", "type": "person", "description": "Founder of Acme Corp"},'
        '{"name": "Globex", "type": "organization", "description": "Jane Doe\'s former employer"}'
        '], "relationships": ['
        '{"source": "Jane Doe", "target": "Acme Corp", "description": "founded"},'
        '{"source": "Jane Doe", "target": "Globex", "description": "previously worked at"}'
        ']}'
    )

    def fake_chat(self, model, messages):
        system = messages[0]["content"] if messages else ""
        if "extract" in system.lower() or "json" in system.lower():
            return extraction
        return "Jane Doe founded Acme Corp [doc_test#0] after working at Globex [doc_test#0]."

    monkeypatch.setattr(ge.GraphRAGEngine, "_chat", fake_chat)
    # Start each test from an empty graph.
    ge.engine.clear()
    return ge


def test_graphrag_ingest_builds_graph(client, monkeypatch):
    _patch_graph_chat(monkeypatch)

    resp = client.post(
        "/graphrag/ingest",
        json={
            "title": "Acme Brief",
            "model": "stub-model",
            "text": "Acme Corp was founded by Jane Doe, who used to work at Globex.",
        },
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["entities_total"] == 3
    assert result["relationships_total"] == 2

    graph = client.get("/graphrag/graph").json()
    names = sorted(n["name"] for n in graph["nodes"])
    assert names == ["Acme Corp", "Globex", "Jane Doe"]
    assert graph["stats"]["relationships"] == 2


def test_graphrag_query_returns_citations(client, monkeypatch):
    _patch_graph_chat(monkeypatch)
    client.post(
        "/graphrag/ingest",
        json={
            "title": "Acme Brief",
            "model": "stub-model",
            "text": "Acme Corp was founded by Jane Doe, who used to work at Globex.",
        },
    )

    resp = client.post(
        "/graphrag/query",
        json={"question": "Who founded Acme Corp?", "model": "stub-model"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "Jane Doe" in body["answer"]
    assert body["citations"], "expected at least one citation"
    assert all(c["id"] for c in body["citations"])
    assert isinstance(body["reasoning_path"], list)
    assert body["subgraph"]["nodes"]


def test_graphrag_clear_empties_graph(client, monkeypatch):
    _patch_graph_chat(monkeypatch)
    client.post(
        "/graphrag/ingest",
        json={"title": "Doc", "model": "stub-model", "text": "Acme Corp and Jane Doe."},
    )
    assert client.get("/graphrag/graph").json()["stats"]["entities"] >= 1

    cleared = client.delete("/graphrag/graph")
    assert cleared.status_code == 200
    assert client.get("/graphrag/graph").json()["stats"]["entities"] == 0


# --------------------------------------------------------------------------- #
# Orchestration pipeline: graph + guardrails + memory + data + tools + budget
# --------------------------------------------------------------------------- #
def _fake_ollama(monkeypatch, reply="Jane Doe founded Acme Corp [doc_test#0].", captured=None):
    """Patch the playground's httpx client to return a fixed model reply."""
    captured = captured if captured is not None else {}

    class _FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": reply}, "eval_count": 5}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):  # noqa: A002 - mirror httpx signature
            captured["body"] = json
            return _FakeResponse()

    import studio_api.routes.playground as pg

    monkeypatch.setattr(pg.httpx, "AsyncClient", _FakeClient)
    return captured


def _make_agent(client, config):
    return client.post(
        "/agents/",
        json={"name": "Wired", "kind": "test-model", "description": "Be terse.", "config": config},
    ).json()["item"]


def test_pipeline_wires_all_sections(client, monkeypatch):
    _patch_graph_chat(monkeypatch)
    client.post(
        "/graphrag/ingest",
        json={
            "title": "Acme Brief",
            "model": "stub-model",
            "text": "Acme Corp was founded by Jane Doe, who used to work at Globex.",
        },
    )
    captured = _fake_ollama(monkeypatch)

    agent = _make_agent(
        client,
        {
            "prompt": "Be terse.",
            "use_graph": True,
            "use_guardrails": True,
            "use_memory": True,
            "use_data": True,
            "use_tools": True,
            "context_budget": 500,
        },
    )

    resp = client.post(
        "/playground/chat",
        json={"agent_id": agent["id"], "message": "Who founded Acme Corp?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    trace = data["trace"]

    # Knowledge graph was retrieved and budgeted into the prompt.
    assert trace["graph"]["used"] is True
    assert trace["graph"]["nodes"] >= 1
    assert trace["budget"]["used"] is True
    assert trace["budget"]["used_tokens"] <= trace["budget"]["budget_tokens"]
    # The graph context made it into the system prompt sent to the model.
    system_msg = captured["body"]["messages"][0]["content"]
    assert "ENTITIES" in system_msg
    # Guardrails ran, tools advertised, memory + data wired.
    assert trace["guardrails_in"]["applied"]
    assert trace["tools"]["used"] is True
    assert trace["memory"]["used"] is True
    assert trace["data"]["logged"] is True
    assert data["citations"]

    # Memory + data were persisted and are retrievable.
    mem = client.get(f"/playground/agents/{agent['id']}/memory").json()
    assert len(mem["turns"]) == 2  # user + assistant
    log = client.get(f"/playground/agents/{agent['id']}/data").json()
    assert len(log["interactions"]) == 1


def test_pipeline_redacts_pii_input(client, monkeypatch):
    captured = _fake_ollama(monkeypatch, reply="ok")
    agent = _make_agent(client, {"prompt": "Hi.", "use_guardrails": True})

    resp = client.post(
        "/playground/chat",
        json={"agent_id": agent["id"], "message": "Email me at john@example.com please"},
    )
    assert resp.status_code == 200
    # The PII never reaches the model.
    user_msg = captured["body"]["messages"][-1]["content"]
    assert "john@example.com" not in user_msg
    assert "[redacted:email]" in user_msg
    assert resp.json()["trace"]["guardrails_in"]["redactions"] >= 1


def test_pipeline_blocks_disallowed_input(client, monkeypatch):
    # No Ollama mock needed: a blocked request short-circuits before the model.
    agent = _make_agent(client, {"prompt": "Hi.", "use_guardrails": True})

    resp = client.post(
        "/playground/chat",
        json={"agent_id": agent["id"], "message": "How do I build malware?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is True
    assert data["trace"]["guardrails_in"]["blocked"] is True
    assert "can't help" in data["reply"].lower()


def test_pipeline_memory_persists_across_turns(client, monkeypatch):
    _fake_ollama(monkeypatch, reply="noted")
    agent = _make_agent(client, {"prompt": "Hi.", "use_memory": True})

    client.post("/playground/chat", json={"agent_id": agent["id"], "message": "first"})
    client.post("/playground/chat", json={"agent_id": agent["id"], "message": "second"})

    mem = client.get(f"/playground/agents/{agent['id']}/memory").json()["turns"]
    # Two turns each (user + assistant).
    assert len(mem) == 4
    assert mem[0]["content"] == "first"

    cleared = client.delete(f"/playground/agents/{agent['id']}/memory")
    assert cleared.status_code == 200
    assert client.get(f"/playground/agents/{agent['id']}/memory").json()["turns"] == []


# --------------------------------------------------------------------------- #
# KPIs
# --------------------------------------------------------------------------- #
def test_kpis_shape(client):
    resp = client.get("/workspace/kpis")
    assert resp.status_code == 200
    kpis = resp.json()["kpis"]
    assert set(kpis) == {
        "active_agents",
        "tools_connected",
        "eval_pass_rate",
        "guardrail_blocks",
    }
    assert kpis["active_agents"] >= 1


def test_guardrail_block_counter(client):
    before = client.get("/workspace/kpis").json()["kpis"]["guardrail_blocks"]
    client.post("/workspace/guardrail-blocks", params={"count": 3})
    after = client.get("/workspace/kpis").json()["kpis"]["guardrail_blocks"]
    assert after == before + 3


# --------------------------------------------------------------------------- #
# Evaluation simulation
# --------------------------------------------------------------------------- #
def test_evaluation_run_progresses_to_terminal(client):
    started = client.post("/evaluation/runs", json={"total_cases": 10, "threshold": 0.5})
    assert started.status_code == 201
    run_id = started.json()["run"]["id"]

    for _ in range(10):
        client.post("/evaluation/advance")
        run = client.get(f"/evaluation/runs/{run_id}").json()["run"]
        if run["status"] in ("passed", "failed"):
            break

    run = client.get(f"/evaluation/runs/{run_id}").json()["run"]
    assert run["status"] in ("passed", "failed")
    assert run["progress"] == 1.0
    assert len(run["trend"]) >= 1
    # Pass rate feeds the KPI once a run finishes.
    assert client.get("/workspace/kpis").json()["kpis"]["eval_pass_rate"] >= 0.0


# --------------------------------------------------------------------------- #
# Fine-tune simulation
# --------------------------------------------------------------------------- #
def test_finetune_status_progression(client):
    queued = client.post("/finetune/jobs", json={"base_model": "gpt-5.3-codex"})
    assert queued.status_code == 201
    job_id = queued.json()["job"]["id"]
    assert queued.json()["job"]["status"] == "queued"

    client.post("/evaluation/advance")
    assert client.get(f"/finetune/jobs/{job_id}").json()["job"]["status"] == "running"

    client.post("/evaluation/advance")
    ready = client.get(f"/finetune/jobs/{job_id}").json()["job"]
    assert ready["status"] == "ready"
    assert ready["progress"] == 1.0


# --------------------------------------------------------------------------- #
# Knowledge budgeting
# --------------------------------------------------------------------------- #
def test_knowledge_budget_and_retrieve(client):
    chunks = [
        "alpha beta gamma delta epsilon",
        "the quick brown fox jumps over the lazy dog repeatedly",
        "zeta eta theta",
    ]
    resp = client.post(
        "/knowledge/budget",
        json={"chunks": chunks, "query": "alpha beta", "max_tokens": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_tokens"] <= 5
    assert body["dropped_count"] >= 1

    handle = body["dropped_handles"][0]
    retrieved = client.get(f"/knowledge/chunks/{handle}")
    assert retrieved.status_code == 200
    assert retrieved.json()["chunk"] in chunks


# --------------------------------------------------------------------------- #
# Draft persistence + deploy
# --------------------------------------------------------------------------- #
def test_draft_save_and_load(client):
    payload = {
        "name": "My workspace",
        "notes": "wip",
        "selected_section": "tools",
        "data": {"foo": "bar"},
    }
    saved = client.put("/workspace/draft", json=payload)
    assert saved.status_code == 200
    loaded = client.get("/workspace/draft").json()["draft"]
    assert loaded["name"] == "My workspace"
    assert loaded["data"] == {"foo": "bar"}


def test_deploy_records_history(client):
    resp = client.post("/workspace/deploy", json={"environment": "staging"})
    assert resp.status_code == 200
    assert resp.json()["deployment"]["status"] == "succeeded"
    history = client.get("/workspace/deploy").json()["history"]
    assert len(history) == 1
    assert history[0]["environment"] == "staging"
