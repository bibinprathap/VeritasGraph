# Agent Studio — Manual Test Guide

Step-by-step manual verification of the `studio_api` backend. Each test lists the
action, the exact command, and the expected result. Run them in order — later
tests build on earlier state.

> All commands assume you are at the repo root (`/home/sijo/VeritasGraph`) with
> the virtualenv active.

---

## 0. Setup

### 0.1 Install dependencies

```sh
source .venv/bin/activate
python3 -m pip install "fastapi>=0.110" "uvicorn[standard]" httpx blake3 pytest
```

**Expected:** installs complete without error. `python3 -c "import fastapi, blake3"` prints nothing (success).

### 0.2 Start the server

Use a fresh data dir and fast simulation steps so progress is visible quickly:

```sh
export STUDIO_DATA_DIR=$(mktemp -d)
export STUDIO_EVAL_STEP_SECONDS=1
export STUDIO_FT_STEP_SECONDS=1
uvicorn studio_api.main:app --host 127.0.0.1 --port 8200 --log-level warning
```

Leave this running in one terminal. Open a **second** terminal for the test
commands below (also run `source .venv/bin/activate` there).

### 0.3 Health check

```sh
curl -s http://127.0.0.1:8200/health
```

**Expected:**
```json
{"status":"ok","version":"1.0.0"}
```

---

## 1. Studio UI & navigation

| # | Action | Command / Step | Expected |
|---|--------|----------------|----------|
| 1.1 | Open the UI | Browse to `http://127.0.0.1:8200/studio` | The Agent Studio page renders with a left **sidebar** listing the 8 sections. |
| 1.2 | Root redirect | `curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" http://127.0.0.1:8200/` | `307 http://127.0.0.1:8200/studio` |
| 1.3 | Sidebar navigation | Click each sidebar item (Agents, Tools, Knowledge, Guardrails, Memory, Data, Evaluation, Fine-tune) | The main panel switches to the selected section; the active item is highlighted. |
| 1.4 | API docs | Browse to `http://127.0.0.1:8200/docs` | Swagger UI lists all section routers. |

---

## 2. KPI header cards

```sh
curl -s http://127.0.0.1:8200/workspace/kpis | python3 -m json.tool
```

**Expected (seed values):**
```json
{
  "message": "KPIs retrieved successfully",
  "kpis": {
    "active_agents": 2,
    "tools_connected": 2,
    "eval_pass_rate": 0.0,
    "guardrail_blocks": 12
  }
}
```

**Check:** the UI header shows four cards matching these numbers. They will
update as you run later tests.

---

## 3. Live inventory panels with status badges

List each collection section and confirm items carry a **status badge**:

```sh
for s in agents tools knowledge guardrails memory data; do
  echo "== $s =="
  curl -s "http://127.0.0.1:8200/$s/" | python3 -c "import sys,json;d=json.load(sys.stdin);print('count',d['count']);[print(' -',i['name'],'=>',i['status']) for i in d['items']]"
done
```

**Expected (seed data):**

| Section | Items & badges |
|---------|----------------|
| agents | Research Orchestrator → `active`, Compliance Reviewer → `active`, Draft Assistant → `draft` |
| tools | Graph Retriever → `connected`, Web Search → `connected`, Code Runner → `disabled` |
| knowledge | Policy Corpus → `indexed`, Product Wiki → `indexing` |
| guardrails | PII Filter → `enforcing`, Toxicity Monitor → `monitoring` |
| memory | Session Memory → `active`, Knowledge Notes → `active` |
| data | Support Tickets → `ready`, Telemetry Stream → `syncing` |

---

## 4. Section builder forms (CRUD)

### 4.1 Create an agent

```sh
curl -s -X POST http://127.0.0.1:8200/agents/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Pricing Analyst","kind":"analyst"}' | python3 -m json.tool
```

**Expected:** HTTP `201`, item returned with `"status": "draft"` (the agents
default badge) and a generated `id` starting `age_`.

### 4.2 Activate it (so it counts toward the KPI)

```sh
AID=$(curl -s http://127.0.0.1:8200/agents/ | python3 -c "import sys,json;print(json.load(sys.stdin)['items'][-1]['id'])")
curl -s -X PATCH http://127.0.0.1:8200/agents/$AID \
  -H "Content-Type: application/json" \
  -d '{"status":"active"}' | python3 -m json.tool
```

**Expected:** `"status": "active"` and a newer `updated_at`.

### 4.3 Verify KPI incremented

```sh
curl -s http://127.0.0.1:8200/workspace/kpis | python3 -c "import sys,json;print('active_agents =',json.load(sys.stdin)['kpis']['active_agents'])"
```

**Expected:** `active_agents = 3`.

### 4.4 Create a tool

```sh
curl -s -X POST http://127.0.0.1:8200/tools/ \
  -H "Content-Type: application/json" \
  -d '{"name":"SQL Runner","kind":"execution"}' | python3 -m json.tool
```

**Expected:** `201`, `"status": "connected"` (tools default badge).
`tools_connected` in the KPIs is now `3`.

### 4.5 Delete a resource

```sh
curl -s -X DELETE http://127.0.0.1:8200/tools/$(curl -s http://127.0.0.1:8200/tools/ | python3 -c "import sys,json;print(json.load(sys.stdin)['items'][-1]['id'])")
```

**Expected:** `{"message":"Resource deleted successfully", ...}`. Re-listing tools
shows one fewer item.

### 4.6 Error handling

```sh
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8200/nonsense/      # unknown section
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8200/agents/missing # unknown id
```

**Expected:** `404` for both.

---

## 5. Guardrails — block counter

```sh
curl -s -X POST "http://127.0.0.1:8200/workspace/guardrail-blocks?count=5" | python3 -m json.tool
```

**Expected:** `"guardrail_blocks"` increased by 5 (e.g. `12` → `17`). The
`guardrail_blocks` KPI card reflects the new total.

---

## 6. Knowledge — context budgeting + CCR retrieval

### 6.1 Budget a set of chunks

```sh
curl -s -X POST http://127.0.0.1:8200/knowledge/budget \
  -H "Content-Type: application/json" \
  -d '{"chunks":["alpha beta gamma pricing model revenue","the quick brown fox jumps over the lazy dog again and again","zeta eta theta iota kappa lambda"],"query":"pricing revenue","max_tokens":7}' \
  | python3 -m json.tool
```

**Expected:**
- `kept` contains the pricing/revenue chunk (highest query overlap).
- `used_tokens` ≤ `7`.
- `dropped_count` ≥ 1 with `dropped_handles` (24-hex strings) and matching
  `markers` of the form `<<ccr:HASH>>`.

### 6.2 Retrieve a dropped chunk by handle

```sh
H=$(curl -s -X POST http://127.0.0.1:8200/knowledge/budget -H "Content-Type: application/json" -d '{"chunks":["alpha beta gamma pricing model revenue","the quick brown fox jumps over the lazy dog again and again","zeta eta theta iota kappa lambda"],"query":"pricing revenue","max_tokens":7}' | python3 -c "import sys,json;print(json.load(sys.stdin)['dropped_handles'][0])")
curl -s http://127.0.0.1:8200/knowledge/chunks/$H | python3 -m json.tool
```

**Expected:** the original dropped chunk text is returned verbatim
(lossless end-to-end). An unknown handle returns `404`.

---

## 7. Evaluation run simulation + trend

### 7.1 Start a run

```sh
RUN=$(curl -s -X POST http://127.0.0.1:8200/evaluation/runs -H "Content-Type: application/json" -d '{"suite":"regression","total_cases":10,"threshold":0.5}' | python3 -c "import sys,json;print(json.load(sys.stdin)['run']['id'])")
echo "run id: $RUN"
```

**Expected:** `201`; a run id starting `eval_`.

### 7.2 Watch the trend converge

Run this a few times (≈1s apart) — the run auto-advances on wall-clock time:

```sh
curl -s http://127.0.0.1:8200/evaluation/runs/$RUN | python3 -c "import sys,json;r=json.load(sys.stdin)['run'];print(r['status'],'progress',round(r['progress'],2),'pass_rate',round(r['pass_rate'],2),'trend_points',len(r['trend']))"
```

**Expected:** `progress` climbs `0.2 → 1.0`, `trend_points` grows each step, and
status ends `passed` (pass_rate ≥ threshold) or `failed`. To force a step
without waiting:

```sh
curl -s -X POST http://127.0.0.1:8200/evaluation/advance
```

### 7.3 Pass rate feeds the KPI

```sh
curl -s http://127.0.0.1:8200/workspace/kpis | python3 -c "import sys,json;print('eval_pass_rate =',json.load(sys.stdin)['kpis']['eval_pass_rate'])"
```

**Expected:** `eval_pass_rate` is now non-zero (e.g. `0.8`).

---

## 8. Fine-tune queue simulation

### 8.1 Queue a job

```sh
JOB=$(curl -s -X POST http://127.0.0.1:8200/finetune/jobs -H "Content-Type: application/json" -d '{"base_model":"gpt-5.3-codex","dataset":"pricing"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['job']['id'])")
echo "job id: $JOB"
```

**Expected:** `201`; status `queued`.

### 8.2 Watch status progression

Call twice (≈1s apart) or force with `/evaluation/advance`:

```sh
curl -s http://127.0.0.1:8200/finetune/jobs/$JOB | python3 -c "import sys,json;j=json.load(sys.stdin)['job'];print(j['status'],'progress',round(j['progress'],2),'loss',j['loss'])"
```

**Expected progression:** `queued → running` (progress 0.5, loss set) `→ ready`
(progress 1.0, loss reduced).

---

## 9. Save draft (server-side persistence)

```sh
curl -s -X PUT http://127.0.0.1:8200/workspace/draft \
  -H "Content-Type: application/json" \
  -d '{"name":"Pricing workspace","notes":"q3","selected_section":"evaluation","data":{"theme":"dark"}}' | python3 -m json.tool

curl -s http://127.0.0.1:8200/workspace/draft | python3 -m json.tool
```

**Expected:** the GET returns exactly what was saved, including nested
`data.theme = "dark"`.

---

## 10. Deploy workspace (mock)

```sh
curl -s -X POST http://127.0.0.1:8200/workspace/deploy \
  -H "Content-Type: application/json" \
  -d '{"environment":"production","notes":"go live"}' | python3 -m json.tool

curl -s http://127.0.0.1:8200/workspace/deploy | python3 -c "import sys,json;print('history entries:',len(json.load(sys.stdin)['history']))"
```

**Expected:** deployment record with `"status": "succeeded"` and a `snapshot` of
the current KPIs; history has at least 1 entry.

---

## 11. Persistence across restart

1. Stop the server (Ctrl-C in the server terminal). **Keep the same
   `STUDIO_DATA_DIR`.**
2. Restart it with the same env vars.
3. Re-fetch the draft:

```sh
curl -s http://127.0.0.1:8200/workspace/draft | python3 -c "import sys,json;print(json.load(sys.stdin)['draft']['name'])"
```

**Expected:** `Pricing workspace` — the draft, resources, KPIs and deploy
history all survived the restart (loaded from `workspace.json` in
`$STUDIO_DATA_DIR`).

---

## 12. Automated regression (optional)

```sh
python3 -m pytest studio_api/tests -v
```

**Expected:** `19 passed` (9 CCR port tests + 10 studio API tests).

---

## Teardown

- Ctrl-C the server terminal.
- The temp `STUDIO_DATA_DIR` can be removed: `rm -rf "$STUDIO_DATA_DIR"`.

---

## Quick checklist

- [ ] Health endpoint returns `ok`
- [ ] UI renders at `/studio`, root redirects there
- [ ] KPI cards show seed values and update live
- [ ] All 6 collection sections list items with status badges
- [ ] Create / activate / delete resource works; KPIs reflect changes
- [ ] Unknown section / id return 404
- [ ] Guardrail block counter increments
- [ ] Knowledge budget keeps top chunk, emits `<<ccr:…>>` markers, retrieves dropped chunk
- [ ] Evaluation run progresses to passed/failed with a growing trend
- [ ] Fine-tune job progresses queued → running → ready
- [ ] Draft saves and reloads with nested data
- [ ] Deploy returns a succeeded record with KPI snapshot + history
- [ ] State persists across a restart
- [ ] `pytest` → 19 passed
