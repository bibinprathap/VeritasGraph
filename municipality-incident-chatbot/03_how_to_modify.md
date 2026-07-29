# 03 — How to Modify

This is the practical guide for changing the system described in
[01_architecture.md](01_architecture.md). Because every capability sits behind an
interface (see [02_why_this_architecture.md](02_why_this_architecture.md)), most
changes touch **one component and its contract only**.

Use the map below to jump to the change you want to make.

| I want to… | Go to |
|------------|-------|
| Add a new incident category (e.g. "graffiti") | [§1](#1-add-a-new-incident-category) |
| Swap or upgrade the computer-vision model | [§2](#2-swap-or-upgrade-the-cv-model) |
| Change the knowledge graph (schema / data / engine) | [§3](#3-change-the-knowledge-graph) |
| Add a new channel (e.g. SMS, kiosk) | [§4](#4-add-a-new-channel) |
| Add or change an external corroboration source | [§5](#5-add-an-external-corroboration-source) |
| Tune the validation thresholds | [§6](#6-tune-validation-scoring--thresholds) |
| Change the case-management target | [§7](#7-change-the-case-management-target) |

Each section lists **what to touch**, **what NOT to touch**, and a **checklist**.

---

## 1. Add a New Incident Category

Example: add `graffiti` reported to the *Public Works* department.

**Touch:**

1. **Knowledge graph** — add an `INCIDENT_TYPE` node:
   ```
   code:          GRAFFITI
   label:         "Graffiti / vandalism"
   cv_labels:     ["spray_paint", "wall_marking"]
   min_confidence: 0.70
   ```
   Link it: `DEPARTMENT(PublicWorks) -[:responsible_for]-> INCIDENT_TYPE(GRAFFITI)`
   and attach an `SLA` (e.g. 72h).
2. **Intent classifier** — add training examples / few-shot phrases that map to
   `GRAFFITI` (or, if using LLM function-calling, add it to the enum).
3. **CV labels** — ensure the detector/verifier can emit the `cv_labels` above
   (see §2 if the model needs retraining or a new prompt).

**Do NOT touch:** channel layer, case service, fusion logic — they read the
category and labels generically from the KG.

**Checklist:**
- [ ] `INCIDENT_TYPE` node + department + SLA relationships added
- [ ] Classifier recognizes the new phrasing
- [ ] `cv_labels` are producible by the CV service
- [ ] Test one report end-to-end → correct department + SLA in the case

---

## 2. Swap or Upgrade the CV Model

The CV service exposes a stable contract:

```jsonc
// request
{ "image_uri": "…", "candidate_labels": ["garbage_overflow", "vehicle"] }
// response
{ "detections": [ { "label": "garbage_overflow", "confidence": 0.91,
                    "bbox": [x, y, w, h] } ], "model": "yolov8n@1.3" }
```

As long as a new model honors this contract, nothing else changes.

**Common swaps:**

| Change | What to do |
|--------|-----------|
| YOLOv8 → YOLOv11 / newer weights | Replace weights + update `model` string; re-benchmark thresholds |
| Add a VLM verifier | Deploy behind the same service; call it only when YOLO confidence is in the gray band (see [02 cost diagram](02_why_this_architecture.md#cost--latency-trade-offs-at-a-glance)) |
| Move to a hosted VLM API (GPT-4o / Gemini) | Implement an adapter that maps the API response into the contract above |
| Add a custom-trained detector | Train on municipal images, export weights, keep the same label vocabulary used in the KG's `cv_labels` |

**Do NOT touch:** orchestrator, fusion, KG — they consume the contract, not the
model internals.

**Checklist:**
- [ ] New model returns the same response shape
- [ ] Label names still match `cv_labels` in the KG (or update both together)
- [ ] Re-tune thresholds in §6 after benchmarking on a validation set
- [ ] Record the `model` version string for audit reproducibility

---

## 3. Change the Knowledge Graph

**Change the data (most common):** add/edit departments, SLAs, policies, or
jurisdictions. This is pure data — no code change. Keep the node/edge shapes from
[01 §4](01_architecture.md#4-knowledge-graph-model).

**Change the schema:** if you add a property or relationship (e.g. a
`SEVERITY` node), update:
1. The graph schema / migration.
2. The **RAG / grounding service** queries that read it.
3. Any answer template that surfaces the new field.

**Swap the engine** (e.g. Neo4j → Cosmos DB Gremlin → RDF): implement a new
adapter behind the grounding service's repository interface:
```
KnowledgeRepository:
  classify(text) -> IncidentType
  route(incidentType) -> Department, SLA
  findSimilar(location, type) -> Case[]
  getPolicy(incidentType) -> Policy
```
Rewrite only the query implementations; callers stay the same.

**Do NOT touch:** vector store (separate concern for semantic search), CV, or
channels.

**Checklist:**
- [ ] Schema migration applied and versioned
- [ ] Grounding queries updated and unit-tested
- [ ] Duplicate / corroboration lookups still return expected neighbors
- [ ] Answer templates render new fields correctly

---

## 4. Add a New Channel

Example: add **SMS** or a physical **kiosk**.

**Touch:** add a channel adapter that translates the channel's messages into the
orchestrator's canonical request:
```jsonc
{ "userId": "…", "text": "…", "attachments": ["blob://…"], "channel": "sms" }
```
Register it at the **API Gateway / BFF**.

**Do NOT touch:** orchestrator, KG, CV, case service — they are channel-agnostic.
Only handle channel-specific limits at the edge (e.g. SMS has no photo → prompt
for an MMS/link, or downgrade the flow).

**Checklist:**
- [ ] Adapter maps inbound/outbound messages to the canonical shape
- [ ] Photo handling defined for the channel (or graceful fallback)
- [ ] Auth / identity resolved at the edge
- [ ] End-to-end test from the new channel

---

## 5. Add an External Corroboration Source

Example: add air-quality sensors or a parking-permit database.

**Touch:** implement a connector behind the **External Connectors** interface:
```
CorroborationSource:
  supports(incidentType, location) -> bool
  fetch(location, timeWindow) -> Evidence[]   // image | telemetry | record
```
Then register it with **Evidence Fusion** and give its signal a weight (§6).

**Do NOT touch:** CV, KG schema (evidence is stored generically as `EVIDENCE`
nodes), or channels.

**Remember:** corroboration is **optional by design** — if the source is down,
fusion must still produce a (lower-confidence) result. Keep the dashed-line
contract from [01 §1](01_architecture.md#1-system-context-diagram).

**Checklist:**
- [ ] Connector implements `supports` + `fetch`
- [ ] Fusion weight assigned; degraded behavior tested (source offline)
- [ ] Evidence persisted to storage + linked to the case
- [ ] No hard dependency introduced

---

## 6. Tune Validation Scoring & Thresholds

Fusion combines signals into one score. Keep the weights and thresholds in
**config**, not code, so tuning needs no redeploy.

```yaml
# fusion.config.yaml (example)
weights:
  citizen_photo_cv: 0.45
  cctv_cv:          0.25
  sensor_telemetry: 0.20
  location_match:   0.10
thresholds:
  auto_validate:    0.80   # ≥ → AUTO_VALIDATED
  needs_review:     0.50   # ≥ and < auto → FOR_REVIEW
                            # < needs_review → REJECTED
caps:
  no_corroboration_max: 0.65   # cap score if CCTV/sensors unavailable
  yolo_only_max:        0.75   # cap if VLM verifier unavailable
```

**How to tune safely:**
1. Assemble a labeled set (real reports marked valid/invalid/duplicate).
2. Sweep thresholds; measure false-accept vs false-reject.
3. Pick thresholds matching municipal risk tolerance (usually minimize
   false auto-dispatch).
4. Roll out behind a flag; monitor the review-queue rate.

**Do NOT touch:** the CV or KG components — tuning is a fusion-config concern.

**Checklist:**
- [ ] Thresholds changed in config only
- [ ] Evaluated on a holdout set
- [ ] Degradation caps still enforced
- [ ] Review-queue volume monitored after rollout

---

## 7. Change the Case-Management Target

Example: move from a custom DB to **ServiceNow** or **Dynamics 365**.

**Touch:** implement the case-sink interface used by the Case Registration
Service:
```
CaseSink:
  create(case, evidenceBundle) -> caseId
  updateStatus(caseId, status) -> void
  findExisting(location, type, window) -> Case[]   // for dedup
```
Swap the adapter; keep the retry/outbox behavior for resilience
(see [02 failure table](02_why_this_architecture.md#failure--degradation-strategy)).

**Do NOT touch:** orchestrator, CV, fusion — they call `CaseSink`, not the vendor
SDK directly.

**Checklist:**
- [ ] Adapter implements create / updateStatus / findExisting
- [ ] Field mapping (category → dept/queue, score → priority) verified
- [ ] Outbox + retry preserved for outages
- [ ] Duplicate lookup still works against the new system

---

## General Rules of Thumb

- **Change data before code.** Categories, departments, SLAs, and thresholds are
  data/config — prefer editing those over writing new logic.
- **Respect the contracts.** If a change stays within a component's interface,
  no other component should need edits. If you *must* change a contract, update
  it in one place and version it.
- **Keep evidence auditable.** Any new signal or model must still write its
  output to the evidence bundle + audit log.
- **Preserve graceful degradation.** New external dependencies must be optional;
  the system should never hard-fail because a corroboration source is offline.
