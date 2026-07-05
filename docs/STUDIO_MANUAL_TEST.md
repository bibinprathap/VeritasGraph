# VeritasGraph Studio — Manual UI Test Guide

A step-by-step checklist to manually verify every feature of the Agent Studio UI
(`demos/agent-studio/index.html`) end-to-end in a browser.

Use the checkboxes (`[ ]` → `[x]`) to track a full pass. Each test lists the
**action**, the **expected result**, and (where relevant) how it maps to the
recent fixes.

---

## 0. Prerequisites & startup

- [ ] **Ollama is running** with at least one model pulled.
  ```bash
  ollama list        # expect e.g. glm-4.7-flash:latest, qwen3.5:latest, ...
  ```
- [ ] **Start the Studio API** (serves both the JSON API and the UI):
  ```bash
  cd /home/sijo/VeritasGraph
  STUDIO_DATA_DIR="$PWD/studio_api/data" \
    .venv/bin/uvicorn studio_api.main:app --host 127.0.0.1 --port 8200 --log-level warning
  ```
- [ ] **Open the UI**: browse to <http://127.0.0.1:8200/> — it should redirect to
  `/studio` and render the "VeritasGraph Studio" workspace.
- [ ] **Hard refresh** (`Ctrl+Shift+R`) to bypass any cached HTML/JS.

> Tip: keep the browser devtools **Console** and **Network** tabs open. There
> should be **no red console errors**, and API calls should return `200`/`204`.

---

## 1. Global shell & navigation

- [ ] The left sidebar shows the **VG** logo and "VeritasGraph Studio / Agent
  Build Workspace".
- [ ] **Runtime status: Healthy** is shown; **Last build** shows a real value
  (`no deploys yet` on a fresh workspace, or a timestamp after a deploy) — **not**
  a hardcoded `2026-06-28` date.
- [ ] The nav lists **10 sections** in order: Agents, Tools, Knowledge,
  Guardrails, Memory, Data, Evaluation, Fine-tune, Playground, Knowledge Graph.
- [ ] Clicking each nav item switches the main panel and updates the **title**
  and **subtitle** in the top bar.
- [ ] The active nav item is highlighted.

### KPI header cards (top of every section)

- [ ] Cards render **real values pulled from the API**, not placeholders. On
  first load they briefly show `—` (an em dash), then populate — you should
  **never** see the old hardcoded `3 / 7 / 93% / 12`.
- [ ] **Active agents** = number of agents with status `active`.
- [ ] **Connected tools** = number of tools with status `connected` (should be a
  small number ~3 in an air-gapped setup, **not** 18 — external mock connectors
  are disabled by default).
- [ ] **Eval pass rate** shows a percentage.
- [ ] **Guardrail blocks** shows an integer.

---

## 2. Agents

### 2a. Create an agent
- [ ] Go to **Agents**.
- [ ] The **model dropdown** ("agentModel") is populated from
  `GET /models/` — it lists only **locally installed** Ollama models (no fake
  placeholders). If none are installed it shows "No local models found".
- [ ] Enter a name (e.g. `Manual Test Agent`), pick a model, type system
  instructions, set tags.
- [ ] Tick some **capability toggles** (Knowledge Graph, Tools, Memory,
  Guardrails, Data log) and set a **Veritasroom context budget** value.
  > Verify the label reads **"Veritasroom context budget (tokens)"** (renamed
  > from "Headroom").
- [ ] Click **Create agent**.
- [ ] **Expected**: the agent appears in the list with capability badges, the
  form clears, and **Active agents** KPI updates if you set it active.

### 2b. Edit an existing agent
- [ ] Click any agent row (or its **Edit** button).
- [ ] **Expected**: the form is populated with that agent's name, model,
  instructions, tags, capability checkboxes, and budget. The primary button
  relabels to **"Update agent"**, a **Cancel** button appears, and the edited row
  is highlighted.
- [ ] Change a field (e.g. toggle Memory on, edit the prompt) and click **Update
  agent**.
- [ ] **Expected**: the change persists (`PATCH /agents/{id}` → `200`), the list
  updates, and the form resets to create mode.
- [ ] Click **Edit**, then **Cancel**.
- [ ] **Expected**: the form clears and returns to "Create agent" without saving.

### 2c. Delete an agent
- [ ] Click **Delete** on the test agent you created.
- [ ] **Expected**: a confirm dialog appears; on confirm the agent is removed
  (`DELETE /agents/{id}`) and the list + KPI update.

### 2d. Orchestration map
- [ ] Confirm the **Orchestration map** card renders and reflects wired
  capabilities.

---

## 3. Tools

- [ ] Go to **Tools**. The **Tool registry** lists seeded tools.
- [ ] **Loopback tools are `connected`**: `Graph Retriever`,
  `VeritasGraph MCP · Query`, `VeritasGraph MCP · Search`.
- [ ] **External mock connectors are `disabled`** by default (Slack, Teams,
  Email, Docs, Sheets, Slides, Cloud Drive, Task Planner, Design Board, GitHub,
  Postman, Power BI, Tableau, AI Assistant Bridge, Web Search) — they can't run
  air-gapped.
- [ ] **Register a tool**: enter a name + endpoint (e.g.
  `http://127.0.0.1:8200/graphrag/query`), click **Register tool**.
- [ ] **Expected**: it appears in the registry; **Connected tools** KPI updates
  if connected.
- [ ] **Tool validation** card renders smoke-check entries.

---

## 4. Knowledge

- [ ] Go to **Knowledge**. Existing knowledge indexes are listed.
- [ ] **Add source**: enter a name, click **Add source**.
- [ ] **Expected**: the new source appears with a status pill.
- [ ] The **Chunking and graph linking** card renders its controls.

---

## 5. Guardrails

- [ ] Go to **Guardrails**. The policy pack lists seeded guardrails (e.g. PII
  Filter, Toxicity Monitor).
- [ ] **Add guardrail**: enter a name, click **Add guardrail** → appears in list.
- [ ] The **Live incidents** card renders.
- [ ] (Enforcement is validated in the Playground — see §9d.)

---

## 6. Memory

- [ ] Go to **Memory**. Memory scopes are listed.
- [ ] **Store memory**: enter a key + value, click **Store memory** → appears in
  the list.
- [ ] The **Memory hygiene** card renders.

---

## 7. Data

- [ ] Go to **Data**. Data connectors are listed.
- [ ] **Add connector**: enter a name, click **Add connector** → appears in list.
- [ ] The **Data quality gates** card renders.

---

## 8. Evaluation & Fine-tune

### 8a. Evaluation
- [ ] Go to **Evaluation**. The suite list and **Performance trend** chart
  render.
- [ ] Pick an eval type (faithfulness / groundedness / latency / policy) and
  click **Run eval**.
- [ ] **Expected**: a new run appears as `queued`/`running` and then advances to
  `passed`/`failed`; the trend line and **Eval pass rate** KPI update. The panel
  auto-refreshes while a run is in progress.

### 8b. Fine-tune
- [ ] Go to **Fine-tune**. The queue and **Safety checks** card render.
- [ ] The **base model** dropdown is populated from installed models.
- [ ] Enter a job name + dataset id, click **Queue job**.
- [ ] **Expected**: the job appears and progresses through statuses; the panel
  auto-refreshes while running.

---

## 9. Playground (core end-to-end)

### 9a. Agent picker
- [ ] Go to **Playground**. The **agent dropdown** lists agents as
  `Name (model)`.
- [ ] Agents whose model is **not installed** show `model — not installed` in the
  option, and the meta line under the picker shows
  `⚠ not installed (will use an available model)`.
- [ ] The **model/status meta line** updates when you switch agents.

### 9b. Chat with an installed-model agent
- [ ] Pick an agent whose model **is** installed (e.g. a `glm-4.7-flash:latest`
  agent).
- [ ] Type a question (e.g. `Say hello in one short sentence.`) and press
  **Enter** or **Send**.
- [ ] **Expected**: a reply appears within a reasonable time (no HTTP 500/502/503
  and no Cloudflare 524). The input re-enables afterward.

### 9c. Model fallback (previously broken → 404)
- [ ] Pick an agent whose model is a **role name / not installed** (e.g.
  `Research Orchestrator`, model `orchestrator`).
- [ ] Send a message.
- [ ] **Expected**: it **still answers** (HTTP 200) and an inline note appears:
  `ℹ Model 'orchestrator' is not installed — running on '<installed model>'.`
  (Previously this returned a 404 "model not found".)

### 9d. Orchestration pipeline trace
After any successful chat, the **Orchestration pipeline** panel should show
stages:
- [ ] **Guardrails (in)** — lists active input guardrails and redaction count.
- [ ] **Memory** — recalled turn count.
- [ ] **Knowledge Graph** — `on/off` with nodes/edges/seeds when graph is wired.
- [ ] **Veritasroom budget** — token usage `used/budget · kept/dropped` (label
  reads **Veritasroom**, not "Headroom").
- [ ] **Tools** — available vs invoked vs skipped counts.
- [ ] **Guardrails (out)** — output redaction count.
- [ ] **Data log** — "interaction recorded".
- [ ] **Reasoning path** + **Tool outputs** + **Citations** render when the graph
  is used.
- [ ] **Skipped (external)** correctly lists disabled external tools as
  *informational* (not errors), and LLM-graph tools show
  "graph answer produced by main model (no extra LLM pass)".

### 9e. Guardrail enforcement (optional deep check)
- [ ] Create/use an agent with **Guardrails** enabled and send input containing
  obvious PII (e.g. a fake email/phone) or blockable content.
- [ ] **Expected**: the reply is redacted/blocked and the **Guardrail blocks**
  KPI increments; the pipeline shows a redaction count > 0.

### 9f. Clear chat
- [ ] Click **Clear chat** → the transcript resets.

---

## 10. Knowledge Graph (GraphRAG)

- [ ] Go to **Knowledge Graph**.
- [ ] The **model** dropdown is populated from installed models.
- [ ] **Ingest a document**: paste a title + a few sentences with clear
  entities/relations (e.g. *"Alice approved the vendor contract with Acme Corp.
  Bob reviewed the budget and flagged a risk."*), click **Ingest document**.
- [ ] **Expected**: extraction runs and the **Graph explorer** shows nodes/edges.
- [ ] **Ask a graph question** (e.g. *"Who approved the vendor contract?"*), click
  **Reason**.
- [ ] **Expected**: a citation-grounded answer appears in **Reasoning path &
  citations**, with a reasoning path and `[doc_...#n]` citations.
- [ ] **Clear graph** → the graph resets (confirm the explorer empties).

---

## 11. Workspace actions (top bar)

- [ ] Click **Save draft**.
- [ ] **Expected**: a success indication; the draft persists (survives a page
  reload).
- [ ] Click **Deploy workspace**.
- [ ] **Expected**: a deploy record is created; **Last build** in the sidebar now
  shows the deploy timestamp (verifies §1's dynamic build label).

---

## 12. Persistence & resilience

- [ ] **Reload the page** (`F5`) — all sections should repopulate from the API
  (agents, tools, KPIs, etc. persist).
- [ ] **Restart the server**, reload — persisted state (agents, tools, memory,
  data, guardrails, drafts) should still be present (stored in
  `studio_api/data/workspace.json`).
- [ ] **Stop Ollama**, then chat in the Playground.
- [ ] **Expected**: a clear error message (HTTP 503 "Could not reach the local
  Ollama runtime…"), not a silent hang or an ugly stack trace.

---

## Quick smoke (5-minute sanity pass)

1. [ ] Open `/studio`, hard refresh — no console errors, KPIs populate.
2. [ ] Create an agent with an installed model → appears in list.
3. [ ] Playground → chat with it → get a reply.
4. [ ] Playground → chat with a `orchestrator`-model agent → get a reply + fallback note.
5. [ ] Knowledge Graph → ingest a short doc → ask a question → get a cited answer.
6. [ ] Edit then delete the test agent → changes persist.

---

### Result log

| Date | Tester | Sections passed | Notes |
|------|--------|-----------------|-------|
|      |        |                 |       |
