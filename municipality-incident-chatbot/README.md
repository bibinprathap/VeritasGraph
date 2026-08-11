# Municipality Incident Reporting Chatbot — Solution Design

A standalone solution design for an AI chatbot that lets citizens report civic
incidents (trash overflow, abandoned vehicles, overcrowding, illegal parking,
etc.) to the **Department of Municipality**. The system accepts a photo,
answers the citizen using a **knowledge graph**, **validates** the complaint
using **computer vision (YOLO / vision-language models)** cross-checked against
**location and other sources (e.g. security camera feeds)**, and finally
**registers a case**.

> This folder contains both the **design documentation** (diagrams, rationale,
> and a modification guide) **and a working reference implementation** in
> [app/](app/), built on the **VeritasGraph** GraphRAG engine. It is
> technology-agnostic and can be implemented on any cloud or on-premises stack.

---

## Document Index

| # | Document | What it covers |
|---|----------|----------------|
| 1 | [01_architecture.md](01_architecture.md) | System context, component, sequence, and data-flow diagrams (Mermaid). |
| 2 | [02_why_this_architecture.md](02_why_this_architecture.md) | Design rationale, trade-offs, and alternatives considered. |
| 3 | [03_how_to_modify.md](03_how_to_modify.md) | How to extend/change each part (new incident types, swap the CV model, change the KG, add channels). |

---

## Running the Reference Implementation

The [app/](app/) package implements the full pipeline on top of VeritasGraph.

```bash
# 1. Install dependencies. The VeritasGraph GraphRAG engine is BUNDLED with
#    this project (see the local studio_api/ folder), so this is all you need.
#    Do NOT `pip install veritasgraph` — that is a different, unrelated project
#    and does not contain studio_api.
pip install -r requirements.txt

# 2. Try it interactively
python cli.py
#   you> trash overflowing near the market | photo=garbage_overflow.jpg | zone=downtown

# 3. Run the test suite (runs fully offline — no GPU / network / LLM needed)
python -m pytest -q
```

**How VeritasGraph is used:** the municipal knowledge graph (incident types →
departments → SLAs → policies) is loaded into the VeritasGraph engine via
`import_graph`, and every complaint is **classified and routed using genuine
multi-hop graph retrieval** (`engine.retrieve`) — the reasoning path is shown to
the citizen.

**Computer vision:** ships with a deterministic **simulated** CV backend so the
whole system runs offline. Set `MUNI_CV_BACKEND=yolo` (and `pip install
ultralytics`) to switch to real YOLO object detection — no other code changes
(see [03_how_to_modify.md](03_how_to_modify.md) §2).

### Code map

| Component (from the architecture) | File |
|-----------------------------------|------|
| Knowledge graph (grounding + routing) | [app/knowledge_graph.py](app/knowledge_graph.py) · [app/seed_data.py](app/seed_data.py) |
| CV validation (YOLO detector + VLM verifier) | [app/cv_service.py](app/cv_service.py) |
| Photo ingest (EXIF / GPS) | [app/exif_utils.py](app/exif_utils.py) |
| External corroboration (CCTV / sensors) | [app/external_sources.py](app/external_sources.py) |
| Evidence fusion & scoring | [app/fusion.py](app/fusion.py) |
| Case registration + dedup | [app/case_service.py](app/case_service.py) |
| Chatbot orchestrator | [app/orchestrator.py](app/orchestrator.py) |
| Tunable weights / thresholds | [app/config.py](app/config.py) |

---

## The Problem in One Line

> "Let a citizen chat, upload a photo, get an intelligent answer, and have a
> **verified** incident automatically routed to the right municipal team — while
> filtering out invalid or duplicate reports **before** a human is involved."

## Core Capabilities

1. **Conversational intake** — natural-language chat (web / WhatsApp / mobile).
2. **Photo upload** — the citizen attaches evidence.
3. **Knowledge-graph answers** — grounded responses (policy, SLA, similar past
   cases, responsible department) instead of hallucinated text.
4. **Automated validation** — a computer-vision pipeline confirms the photo
   actually shows the reported problem; location + external sources (CCTV,
   sensors, prior reports) corroborate it.
5. **Case registration** — a structured ticket is created in the municipal
   case-management system with a confidence score and evidence bundle.

## Supported Incident Categories (initial)

- Trash / garbage overflow
- Abandoned vehicle
- Overcrowding
- Illegal parking
- *(extensible — see [03_how_to_modify.md](03_how_to_modify.md))*

## Validation Outcomes

| Outcome | Meaning | Action |
|---------|---------|--------|
| ✅ Auto-validated | CV + location + corroboration agree, high confidence | Case created, routed to department |
| 🟡 Needs review | Partial evidence / medium confidence | Case created, flagged for human triage |
| ❌ Rejected | No matching evidence / duplicate / out of jurisdiction | Citizen informed with reason, no case (or merged into existing) |
