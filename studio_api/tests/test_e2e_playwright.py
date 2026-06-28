"""Playwright end-to-end tests for the Agent Studio.

These automate the manual test guide (``studio_api/MANUAL_TEST.md``) against a
real, running server:

* **API tests** use Playwright's :class:`APIRequestContext` to hit every backend
  endpoint exactly as the ``curl`` steps do.
* **UI tests** drive the studio page in a real Chromium browser (sidebar
  navigation, KPI cards, builder forms, save/deploy actions).

The server is started once per session against a throwaway data dir with fast
simulation steps, then torn down.

Run with::

    python3 -m pytest studio_api/tests/test_e2e_playwright.py -v
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import APIRequestContext, Page, expect, sync_playwright

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server():
    """Start uvicorn against a fresh data dir; yield the base URL."""
    port = _free_port()
    data_dir = tempfile.mkdtemp(prefix="studio-e2e-")
    env = {
        **os.environ,
        "STUDIO_DATA_DIR": data_dir,
        "STUDIO_EVAL_STEP_SECONDS": "1",
        "STUDIO_FT_STEP_SECONDS": "1",
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "studio_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                "server exited early:\n"
                + (proc.stdout.read().decode() if proc.stdout else "")
            )
        try:
            if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                break
        except Exception:
            time.sleep(0.25)
    else:
        proc.terminate()
        raise RuntimeError("server did not become healthy in time")

    yield {"base": base, "data_dir": data_dir, "proc": proc}

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def playwright_ctx():
    with sync_playwright() as p:
        yield p


@pytest.fixture()
def api(server, playwright_ctx) -> APIRequestContext:
    ctx = playwright_ctx.request.new_context(base_url=server["base"])
    yield ctx
    ctx.dispose()


@pytest.fixture()
def page(server, playwright_ctx):
    # Use the real Google Chrome browser (channel="chrome") rather than the
    # bundled Chromium build.
    browser = playwright_ctx.chromium.launch(channel="chrome")
    pg = browser.new_page()
    # The studio UI is now wired to the backend, so serve it from the API.
    pg.goto(f"{server['base']}/studio")
    # Wait until the first data load populates the seeded agents.
    expect(pg.locator("#agentList > div").first).to_be_visible()
    yield pg
    browser.close()


# =========================================================================== #
# 0. Setup / health
# =========================================================================== #
def test_0_health(api):
    resp = api.get("/health")
    assert resp.status == 200
    assert resp.json() == {"status": "ok", "version": "1.0.0"}


# =========================================================================== #
# 1. UI & navigation (served by the API)
# =========================================================================== #
def test_1_root_redirects_to_studio(api):
    resp = api.get("/", max_redirects=0)
    assert resp.status == 307
    assert resp.headers["location"].endswith("/studio")


def test_1_studio_ui_served(api):
    resp = api.get("/studio")
    assert resp.status == 200
    assert "Agent Studio" in resp.text()


def test_1_openapi_lists_routers(api):
    paths = api.get("/openapi.json").json()["paths"]
    for prefix in ["/agents/", "/tools/", "/evaluation/runs", "/finetune/jobs", "/workspace/kpis"]:
        assert any(p.startswith(prefix) for p in paths), prefix


# =========================================================================== #
# 2. KPI header cards
# =========================================================================== #
def test_2_kpi_seed_values(api):
    kpis = api.get("/workspace/kpis").json()["kpis"]
    assert set(kpis) == {"active_agents", "tools_connected", "eval_pass_rate", "guardrail_blocks"}
    assert kpis["active_agents"] >= 2
    assert kpis["tools_connected"] >= 2


# =========================================================================== #
# 3. Inventory panels with status badges
# =========================================================================== #
def test_3_all_sections_have_badged_items(api):
    expected = {
        "agents": {"active", "draft"},
        "tools": {"connected", "disabled"},
        "knowledge": {"indexed", "indexing"},
        "guardrails": {"enforcing", "monitoring"},
        "memory": {"active"},
        "data": {"ready", "syncing"},
    }
    for section, badges in expected.items():
        body = api.get(f"/{section}/").json()
        assert body["count"] >= 1, section
        statuses = {i["status"] for i in body["items"]}
        assert statuses & badges, (section, statuses)


# =========================================================================== #
# 4. Section builder forms (CRUD)
# =========================================================================== #
def test_4_resource_crud_and_kpi(api):
    before = api.get("/workspace/kpis").json()["kpis"]["active_agents"]

    created = api.post("/agents/", data={"name": "Pricing Analyst", "kind": "analyst"})
    assert created.status == 201
    item = created.json()["item"]
    assert item["status"] == "draft"
    assert item["id"].startswith("age_")

    activated = api.patch(f"/agents/{item['id']}", data={"status": "active"})
    assert activated.status == 200
    assert activated.json()["item"]["status"] == "active"

    after = api.get("/workspace/kpis").json()["kpis"]["active_agents"]
    assert after == before + 1

    tool = api.post("/tools/", data={"name": "SQL Runner", "kind": "execution"})
    assert tool.status == 201
    assert tool.json()["item"]["status"] == "connected"
    tid = tool.json()["item"]["id"]

    deleted = api.delete(f"/tools/{tid}")
    assert deleted.status == 200
    assert api.get(f"/tools/{tid}").status == 404


def test_4_error_handling(api):
    assert api.get("/nonsense/").status == 404
    assert api.get("/agents/does-not-exist").status == 404


# =========================================================================== #
# 5. Guardrail block counter
# =========================================================================== #
def test_5_guardrail_block_counter(api):
    before = api.get("/workspace/kpis").json()["kpis"]["guardrail_blocks"]
    resp = api.post("/workspace/guardrail-blocks", params={"count": "5"})
    assert resp.status == 200
    assert resp.json()["guardrail_blocks"] == before + 5
    assert api.get("/workspace/kpis").json()["kpis"]["guardrail_blocks"] == before + 5


# =========================================================================== #
# 6. Knowledge budgeting + CCR retrieval
# =========================================================================== #
_CHUNKS = [
    "alpha beta gamma pricing model revenue",
    "the quick brown fox jumps over the lazy dog again and again",
    "zeta eta theta iota kappa lambda",
]


def test_6_knowledge_budget_and_retrieve(api):
    resp = api.post(
        "/knowledge/budget",
        data={"chunks": _CHUNKS, "query": "pricing revenue", "max_tokens": 7},
    )
    assert resp.status == 200
    body = resp.json()
    assert body["used_tokens"] <= 7
    assert _CHUNKS[0] in body["kept"]
    assert body["dropped_count"] >= 1
    handle = body["dropped_handles"][0]
    assert len(handle) == 24
    assert f"<<ccr:{handle}>>" in body["markers"]

    retrieved = api.get(f"/knowledge/chunks/{handle}")
    assert retrieved.status == 200
    assert retrieved.json()["chunk"] in _CHUNKS

    assert api.get("/knowledge/chunks/deadbeef").status == 404


# =========================================================================== #
# 7. Evaluation run simulation + trend
# =========================================================================== #
def test_7_evaluation_run_progresses(api):
    run = api.post(
        "/evaluation/runs",
        data={"suite": "regression", "total_cases": 10, "threshold": 0.5},
    ).json()["run"]
    assert run["id"].startswith("eval_")

    for _ in range(12):
        api.post("/evaluation/advance")
        run = api.get(f"/evaluation/runs/{run['id']}").json()["run"]
        if run["status"] in ("passed", "failed"):
            break

    assert run["status"] in ("passed", "failed")
    assert run["progress"] == 1.0
    assert len(run["trend"]) >= 1
    assert api.get("/workspace/kpis").json()["kpis"]["eval_pass_rate"] >= 0.0


# =========================================================================== #
# 8. Fine-tune queue simulation
# =========================================================================== #
def test_8_finetune_progression(api):
    job = api.post(
        "/finetune/jobs", data={"base_model": "gpt-5.3-codex", "dataset": "pricing"}
    ).json()["job"]
    assert job["status"] == "queued"

    api.post("/evaluation/advance")
    assert api.get(f"/finetune/jobs/{job['id']}").json()["job"]["status"] == "running"

    api.post("/evaluation/advance")
    ready = api.get(f"/finetune/jobs/{job['id']}").json()["job"]
    assert ready["status"] == "ready"
    assert ready["progress"] == 1.0


# =========================================================================== #
# 9. Save draft (server-side persistence)
# =========================================================================== #
def test_9_draft_round_trip(api):
    payload = {
        "name": "Pricing workspace",
        "notes": "q3",
        "selected_section": "evaluation",
        "data": {"theme": "dark"},
    }
    assert api.put("/workspace/draft", data=payload).status == 200
    draft = api.get("/workspace/draft").json()["draft"]
    assert draft["name"] == "Pricing workspace"
    assert draft["data"] == {"theme": "dark"}


# =========================================================================== #
# 10. Deploy workspace (mock)
# =========================================================================== #
def test_10_deploy_records_history(api):
    resp = api.post("/workspace/deploy", data={"environment": "production", "notes": "go live"})
    assert resp.status == 200
    dep = resp.json()["deployment"]
    assert dep["status"] == "succeeded"
    assert "snapshot" in dep
    assert len(api.get("/workspace/deploy").json()["history"]) >= 1


# =========================================================================== #
# 11. Persistence across restart
# =========================================================================== #
def test_11_state_persists_across_restart(server):
    # Save a marker, then spin up a second app process on the SAME data dir.
    base = server["base"]
    httpx.put(
        f"{base}/workspace/draft",
        json={"name": "Persisted WS", "notes": "", "selected_section": "data", "data": {"k": 1}},
        timeout=5,
    )

    port = _free_port()
    env = {
        **os.environ,
        "STUDIO_DATA_DIR": server["data_dir"],
        "STUDIO_EVAL_STEP_SECONDS": "1",
        "STUDIO_FT_STEP_SECONDS": "1",
    }
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "studio_api.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ],
        cwd=str(_REPO_ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        base2 = f"http://127.0.0.1:{port}"
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if httpx.get(f"{base2}/health", timeout=1).status_code == 200:
                    break
            except Exception:
                time.sleep(0.25)
        draft = httpx.get(f"{base2}/workspace/draft", timeout=5).json()["draft"]
        assert draft["name"] == "Persisted WS"
        assert draft["data"] == {"k": 1}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# =========================================================================== #
# UI tests (real browser against the static studio page)
# =========================================================================== #
def test_ui_sidebar_lists_eight_sections(page: Page):
    expect(page.locator(".nav button")).to_have_count(10)
    for label in ["Agents", "Tools", "Knowledge", "Guardrails", "Memory", "Data", "Evaluation", "Fine-tune", "Playground", "Knowledge Graph"]:
        # Exact match: "Knowledge" is a substring of "Knowledge Graph".
        expect(page.get_by_role("button", name=label, exact=True)).to_have_count(1)


def test_ui_kpi_cards_present(page: Page):
    for kpi_id in ["kpiAgents", "kpiTools", "kpiEval", "kpiBlocks"]:
        expect(page.locator(f"#{kpi_id}")).to_be_visible()


def test_ui_navigation_switches_sections(page: Page):
    # Agents is the default active section.
    expect(page.locator("#agents")).to_have_class(re.compile(r"\bactive\b"))
    page.locator(".nav button", has_text="Guardrails").click()
    expect(page.locator("#guardrails")).to_have_class(re.compile(r"\bactive\b"))
    expect(page.locator("#screenTitle")).to_have_text("Guardrails")

    page.locator(".nav button", has_text="Fine-tune").click()
    expect(page.locator("#fine-tune")).to_have_class(re.compile(r"\bactive\b"))
    expect(page.locator("#screenTitle")).to_have_text("Fine-tune")


def test_ui_create_agent_appends_to_list(page: Page):
    before = page.locator("#agentList > div").count()
    page.fill("#agentName", "QA Bot")
    page.fill("#agentTags", "qa,test")
    page.click("#addAgent")
    # The agent is POSTed to the backend, then the list reloads from the API.
    expect(page.locator("#agentList > div")).to_have_count(before + 1)
    expect(page.locator("#agentList")).to_contain_text("QA Bot")


def test_ui_run_eval_updates_kpi(page: Page):
    page.locator(".nav button", has_text="Evaluation").click()
    page.click("#runEval")
    # KPI text becomes a percentage like "92%".
    expect(page.locator("#kpiEval")).to_have_text(re.compile(r"%$"))


def test_ui_save_draft_persists_to_backend(page: Page, server):
    page.on("dialog", lambda d: d.accept())
    with page.expect_event("dialog"):
        page.click("#saveBtn")
    draft = httpx.get(f"{server['base']}/workspace/draft", timeout=5).json()["draft"]
    assert draft["name"] == "VeritasGraph workspace"


def test_ui_deploy_shows_dialog(page: Page):
    messages = []
    page.on("dialog", lambda d: (messages.append(d.message), d.accept()))
    with page.expect_event("dialog"):
        page.click("#deployBtn")
    assert any("deployment" in m.lower() for m in messages)


def test_ui_playground_lists_agents(page: Page):
    page.locator(".nav button", has_text="Playground").click()
    expect(page.locator("#playground")).to_have_class(re.compile(r"\bactive\b"))
    # The agent selector is populated from the backend agents. <option> elements
    # live inside a closed <select>, so assert on count/value rather than visibility.
    expect(page.locator("#playgroundAgent")).to_be_visible()
    assert page.locator("#playgroundAgent option").count() >= 1
    assert page.locator("#playgroundAgent").input_value().startswith("age_")
    expect(page.locator("#chatLog")).to_be_visible()


def test_ui_knowledge_graph_section_renders(page: Page):
    page.get_by_role("button", name="Knowledge Graph", exact=True).click()
    expect(page.locator("#graphrag")).to_have_class(re.compile(r"\bactive\b"))
    # Core controls are present.
    expect(page.locator("#graphText")).to_be_visible()
    expect(page.locator("#graphCanvas")).to_be_visible()
    expect(page.locator("#graphQuestion")).to_be_visible()
    # Model selector is populated (or shows the empty-state option).
    assert page.locator("#graphModel option").count() >= 1


def test_ui_agent_capabilities_persist_to_config(page: Page, server):
    # Wire studio capabilities into a new agent and verify they reach the backend.
    page.fill("#agentName", "Wired Agent")
    page.check("#capGraph")
    page.check("#capGuardrails")
    page.check("#capMemory")
    page.fill("#capBudget", "450")
    before = page.locator("#agentList > div").count()
    page.click("#addAgent")
    expect(page.locator("#agentList > div")).to_have_count(before + 1)
    # The capability badges render on the agent card.
    expect(page.locator("#agentList")).to_contain_text("Graph")
    expect(page.locator("#agentList")).to_contain_text("Memory")

    # The backend stored the capability flags in the agent's config.
    agents = httpx.get(f"{server['base']}/agents/", timeout=5).json()["items"]
    wired = next(a for a in agents if a["name"] == "Wired Agent")
    assert wired["config"]["use_graph"] is True
    assert wired["config"]["use_guardrails"] is True
    assert wired["config"]["use_memory"] is True
    assert wired["config"]["context_budget"] == 450


def test_ui_pipeline_panel_present(page: Page):
    page.get_by_role("button", name="Playground", exact=True).click()
    expect(page.locator("#pipelineTrace")).to_be_visible()
    expect(page.locator(".pipeline-empty")).to_be_visible()
