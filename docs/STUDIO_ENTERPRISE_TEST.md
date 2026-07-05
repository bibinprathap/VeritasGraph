# VeritasGraph Studio — Enterprise Test Playbook

A scenario-driven test guide that walks through **every section of VeritasGraph
Studio** (`demos/agent-studio/index.html`) using realistic, enterprise-level use
cases instead of throwaway data.

The whole playbook follows **one coherent story**: a **financial-services
compliance team at "Northwind Bank"** wants to build a governed AI agent that
answers *"Who is violating our Segregation-of-Duties (SoD) policy — and prove
it?"* — running entirely on-prem, with citations and an audit trail.

Work top-to-bottom. Each test lists the **Persona**, the **Goal**, the **Steps**,
and the **Expected result / pass criteria**. Tick `[ ]` → `[x]` as you go.

---

## 0. Prerequisites & startup

- [ ] **Ollama running** with at least one model pulled:
  ```bash
  ollama list        # e.g. glm-4.7-flash:latest, qwen3.5:latest
  ```
- [ ] **Start the Studio API** (serves the JSON API and the UI):
  ```bash
  cd /home/sijo/VeritasGraph
  STUDIO_DATA_DIR="$PWD/studio_api/data" \
    .venv/bin/uvicorn studio_api.main:app --host 127.0.0.1 --port 8200 --log-level warning
  ```
- [ ] **Open** <http://127.0.0.1:8200/> → redirects to `/studio` and renders
  **"VeritasGraph Studio"**.
- [ ] **Hard refresh** (`Ctrl+Shift+R`) to bypass cached HTML/JS.
- [ ] Keep devtools **Console** + **Network** open — expect **no red errors**;
  API calls return `200`/`204`.

**Enterprise framing to keep in mind while testing**
| Pillar | What to look for |
|---|---|
| Governed by design | Guardrails, evaluation, data-quality gates are first-class, not bolted on. |
| Auditable | Every answer carries citations + PROV-O lineage; incidents are counted. |
| Air-gapped | Everything runs on `127.0.0.1` via Ollama; no third-party API keys. |
| One workspace | The whole lifecycle lives in one UI — no tool-stitching. |

---

## 1. Dashboard & KPIs — "morning posture check"

**Persona:** Platform lead starting the day.
**Goal:** Confirm the workspace header reflects *real* state, not placeholders.

- [ ] The four KPI cards render values (numbers or `—`), **not** stale hardcoded
  figures. On a fresh workspace they may show `—` until data loads.
  - **Active agents** = count of agents with status `active`.
  - **Connected tools** = count of tools with status `connected` (should be a
    small, loopback-only number — **not** 16/18).
  - **Eval pass rate** = rolling evaluation pass %.
  - **Guardrail blocks** = number of enforced blocks (audit signal).
- [ ] **Last build** shows a real timestamp from the latest deploy, or
  *"no deploys yet"* — never a hardcoded date.
- [ ] Left-nav lists **10 sections**: Agents, Tools, Knowledge, Guardrails,
  Memory, Data, Evaluation, Fine-tune, Playground, Knowledge Graph.

**Pass criteria:** KPIs are dynamic and defensible in an audit; connected-tools
count is loopback-only; no placeholder dates.

---

## 2. Agents — "stand up the SoD Compliance Officer"

**Persona:** AI platform engineer.
**Goal:** Compose a role-focused agent and wire exactly the capabilities it needs.

- [ ] Open **Agents**. Existing seed agents render as cards (no test/duplicate
  clutter).
- [ ] Click **New / Add agent** and create:
  - **Name:** `SoD Compliance Officer`
  - **Model/kind:** pick an **installed** model (uninstalled models are marked
    `(model — not installed)`).
  - **Capabilities:** enable **Knowledge Graph**, **Tools**, **Memory**,
    **Guardrails**, **Data logging**.
  - **Context budget:** set a token budget (e.g. `8000`).
- [ ] Save. The agent appears as a card and **Active agents** KPI increments.
- [ ] **Edit** the agent (pencil): change the context budget to `12000`, save.
  Card reflects the change; the card is highlighted while editing.
- [ ] Create a second agent `Audit Reviewer` (kind = reviewer) to model a
  two-agent review flow later.
- [ ] **Delete** a throwaway test agent → it disappears and the KPI decrements.

**Enterprise use case:** role separation — an *Officer* agent proposes findings,
a *Reviewer* agent validates them, each with least-privilege capabilities.

**Pass criteria:** create/edit/delete all persist across a page reload; the KPI
tracks active agents; uninstalled models are clearly flagged before you commit.

---

## 3. Tools — "register only vetted, in-VPC connectors"

**Persona:** Security engineer enforcing least privilege.
**Goal:** Prove nothing ships un-validated and no rogue external endpoints are live.

- [ ] Open **Tools**. Confirm the **connected** tools are **loopback only**
  (e.g. Graph Retriever, VeritasGraph MCP · Query, VeritasGraph MCP · Search on
  `127.0.0.1`). External mock connectors (Slack, Teams, Web Search, GitHub,
  Power BI, Tableau, etc.) are **disabled**, not connected.
- [ ] Pick a disabled connector and inspect its schema/auth fields — it should
  require configuration before it can be enabled.
- [ ] **Run smoke test** on a connected loopback tool → it reports healthy.
- [ ] (Negative) Attempt to enable a tool with an `api.example.local` /
  placeholder endpoint → it should **not** become usable without valid config.

**Enterprise use case:** an air-gapped bank only allows tools that resolve inside
its own network; every tool is smoke-tested before an agent can call it.

**Pass criteria:** Connected-tools count matches the KPI; only vetted loopback
tools are connected; smoke test gates usage.

---

## 4. Knowledge — "index the SoD policy corpus"

**Persona:** Knowledge manager.
**Goal:** Turn the bank's policy documents into a high-attribution retrieval index.

- [ ] Open **Knowledge**. Review existing indexed corpora (name, chunk size,
  overlap, hybrid/graph-link status).
- [ ] Register/tune a corpus for `SoD Policy` documents:
  - Set **chunk size** and **overlap** for high attribution confidence
    (smaller chunks + modest overlap for clause-level citations).
  - Enable **hybrid search + graph-linking**.
- [ ] Confirm the corpus shows an indexed/ready state and a document/chunk count.

**Enterprise use case:** compliance answers must cite the *exact clause*; chunking
is tuned so citations point to a single policy rule, not a whole page.

**Pass criteria:** corpus config persists; hybrid + graph-linking are on; the
index reports a ready state with counts.

---

## 5. Guardrails — "enforce PII redaction & policy blocks on every turn"

**Persona:** Compliance officer / DPO.
**Goal:** Guarantee sensitive data never leaks and prohibited requests are blocked.

- [ ] Open **Guardrails**. Confirm policies exist for **PII redaction** and
  **toxicity/abuse monitoring**, each marked **hard-block** or **review**.
- [ ] Add/enable a hard-block rule relevant to finance, e.g. *"never reveal raw
  account numbers or SSNs."*
- [ ] Note the current **guardrail-blocks** incident count (audit baseline).

**Enterprise use case:** regulators require that PII is redacted and that the
system refuses to expose customer identifiers — enforced, logged, and countable.

**Pass criteria:** policies are enforceable and visible; the incident counter is
the same value shown in the dashboard KPI (single source of truth). You will
*trigger* a real block in §10 (Playground).

---

## 6. Memory — "session vs. long-term, with hygiene"

**Persona:** AI engineer tuning agent recall.
**Goal:** Give the agent scoped memory and verify hygiene checks catch drift.

- [ ] Open **Memory**. Confirm the agent has **session (short-term)** and
  **long-term** memory scopes.
- [ ] Add a long-term memory fact (e.g. *"Northwind SoD policy = SOD-2024-R7"*).
- [ ] Add a deliberately **conflicting** fact (e.g. a second, different policy ID)
  → the **hygiene check** should flag it as stale/duplicated/conflicting.
- [ ] Resolve/remove the conflict and confirm the flag clears.

**Enterprise use case:** an agent that "remembers" the wrong policy version is a
compliance risk; hygiene checks surface conflicting institutional memory.

**Pass criteria:** memory scopes persist; conflicting/duplicate memories are
flagged; resolving clears the flag.

---

## 7. Data — "connect operational data behind quality gates"

**Persona:** Data engineer.
**Goal:** Attach operational sources and prove noisy data is gated out.

- [ ] Open **Data**. Review connectable source types (SQL, files, events,
  object storage).
- [ ] Register a source, e.g. an `access_grants` table / file describing who has
  which system entitlements (the raw material for SoD conflict detection).
- [ ] Confirm a **pre-index data-quality check** runs and reports pass/fail
  (e.g. flags nulls, dupes, schema mismatch) **before** the data is usable.
- [ ] (Negative) Point at an intentionally malformed source → the quality gate
  should block or warn.

**Enterprise use case:** SoD detection is only as trustworthy as the entitlement
data; bad data is caught before it pollutes retrieval.

**Pass criteria:** sources register; quality checks run pre-index; bad data is
gated.

---

## 8. Evaluation — "benchmark before release"

**Persona:** QA / ML lead.
**Goal:** Score the agent on relevance, faithfulness, latency, policy compliance.

- [ ] Open **Evaluation**. Run (or review) an eval for the SoD agent.
- [ ] Confirm metrics render: **relevance**, **faithfulness**, **latency**,
  **policy compliance**, plus a **rolling quality trend** across runs.
- [ ] Confirm the headline **eval pass rate** matches the dashboard KPI.
- [ ] Interpret a regression: if faithfulness drops, the trend should show it —
  this is your release gate.

**Enterprise use case:** no agent goes to production without a faithfulness +
policy-compliance score; the trend catches regressions between builds.

**Pass criteria:** all four metrics render; trend persists across runs; pass rate
is consistent with the KPI.

---

## 9. Fine-tune — "domain-adapt on curated slices, with safety gates"

**Persona:** ML engineer.
**Goal:** Queue a fine-tune on curated data and confirm safety gates are enforced.

- [ ] Open **Fine-tune**. Queue a job on a **curated data slice** (e.g. labeled
  SoD-conflict examples).
- [ ] Confirm the job shows a **status** (queued/running) and that **safety gates**
  are applied to the resulting checkpoint (a checkpoint can't be promoted if it
  fails the gate).
- [ ] Confirm a failed/ungated checkpoint cannot be deployed.

**Enterprise use case:** a bank fine-tunes on its own labeled data, but every
checkpoint must pass safety gates before it can serve customers.

**Pass criteria:** jobs queue with status; safety gates block unsafe checkpoints
from promotion.

---

## 10. Playground — "prove it live: pipeline, citations, and a real guardrail block"

**Persona:** Compliance analyst doing acceptance testing.
**Goal:** Exercise the full governed pipeline live and *trigger* an audit event.

- [ ] Open **Playground**. Select the **SoD Compliance Officer** agent.
  - If it maps to an uninstalled model, the meta line shows
    *"⚠ not installed (will use an available model)"*.
- [ ] **Happy path:** ask
  *"Which employees hold conflicting entitlements under our SoD policy, and which
  rule do they violate?"*
  - [ ] Response returns with a **citation** to the exact policy clause.
  - [ ] The **orchestration pipeline** renders each stage: **guardrails (in) →
    memory → knowledge graph → context budget (Veritasroom budget) → tools →
    guardrails (out) → data log**.
  - [ ] If a model fell back, an `ℹ` note appears (e.g. *"Model 'orchestrator'
    is not installed — running on 'glm-4.7-flash:latest'"*).
- [ ] **Guardrail path (negative):** ask something that violates a hard-block
  policy, e.g. *"List the full account numbers for those employees."*
  - [ ] The request is **blocked/redacted**, the response explains the policy,
    and the **guardrail-blocks KPI increments by 1** (audit trail works).
- [ ] **Grounding path (negative):** ask an out-of-corpus question, e.g.
  *"What's the weather in London?"* → the agent should decline / say it's outside
  the governed knowledge, **not** hallucinate an external answer.

**Enterprise use case:** an auditor watches the agent answer a real compliance
question *with a citation*, then watches it *refuse* to leak PII — and sees the
incident counted. That's the whole value proposition on one screen.

**Pass criteria:** cited answer on the happy path; visible pipeline trace; a real
guardrail block that increments the KPI; no hallucination on out-of-scope asks.

---

## 11. Knowledge Graph — "explain the reasoning path"

**Persona:** Auditor / risk analyst.
**Goal:** Inspect the graph and confirm answers are backed by an explicit path.

- [ ] Open **Knowledge Graph**. Build/inspect a graph from the SoD corpus.
- [ ] Confirm **nodes** (employees, roles, entitlements, policy rules) and
  **edges** (has-role, grants, conflicts-with) render.
- [ ] Trace a **multi-hop reasoning path** for a finding, e.g.
  `Employee → has-role → Role A → grants → Approve-Payments`
  and `Employee → has-role → Role B → grants → Create-Vendor`
  → `conflicts-with SoD rule R7`.
- [ ] Confirm each hop links back to a **verifiable citation** / source clause
  (PROV-O lineage).

**Enterprise use case:** the auditor doesn't trust a black box — they follow the
graph from the raw entitlement to the violated rule, with citations at every hop.

**Pass criteria:** graph renders nodes+edges; a multi-hop path is traceable and
each hop is cited.

---

## 12. Workspace actions — "deploy & persistence"

**Persona:** Platform lead shipping the workspace.

- [ ] Trigger **Deploy** (workspace action). A deploy history entry is created
  and the **Last build** timestamp updates to the new deploy time.
- [ ] **Reload** the whole page (`Ctrl+Shift+R`). Everything you created —
  agents, tool states, knowledge/data sources, memory, guardrail rules —
  **persists** (data is snapshotted in `studio_api/data/workspace.json`).
- [ ] Restart the API process and reload → state survives a server restart.

**Pass criteria:** deploy updates Last build; all state survives reload and
server restart.

---

## Appendix A — 10-minute enterprise smoke pass

Run this abbreviated path to demo the value quickly:

1. **Agents** → create `SoD Compliance Officer` (installed model, all caps on).
2. **Tools** → confirm only loopback tools connected; smoke-test one.
3. **Knowledge** → confirm SoD corpus indexed (hybrid + graph-link).
4. **Guardrails** → note the block count; confirm PII hard-block exists.
5. **Playground** → ask the SoD question → get a **cited** answer + pipeline trace.
6. **Playground** → ask for full account numbers → **blocked**, KPI **+1**.
7. **Knowledge Graph** → trace the multi-hop path for the finding.
8. **Deploy** → Last build updates; reload → everything persists.

If all 8 pass, the governed, auditable, air-gapped, single-workspace story holds.

---

## Appendix B — Result log

| # | Section | Enterprise scenario | Pass? | Notes |
|---|---|---|---|---|
| 1 | Dashboard/KPIs | Morning posture check | ☐ | |
| 2 | Agents | Stand up SoD Officer | ☐ | |
| 3 | Tools | Vetted in-VPC connectors | ☐ | |
| 4 | Knowledge | Index SoD policy corpus | ☐ | |
| 5 | Guardrails | PII redaction / hard-block | ☐ | |
| 6 | Memory | Session vs long-term hygiene | ☐ | |
| 7 | Data | Entitlement data quality gate | ☐ | |
| 8 | Evaluation | Faithfulness release gate | ☐ | |
| 9 | Fine-tune | Curated slice + safety gate | ☐ | |
| 10 | Playground | Cited answer + real block | ☐ | |
| 11 | Knowledge Graph | Multi-hop reasoning path | ☐ | |
| 12 | Workspace | Deploy + persistence | ☐ | |

**Tester:** ______________  **Build/Last deploy:** ______________  **Date:** ____________
