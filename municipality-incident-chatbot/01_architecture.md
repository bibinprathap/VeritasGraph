# 01 — Architecture

This document shows the architecture from four angles:

1. **System context** — who/what interacts with the system.
2. **Component architecture** — the internal building blocks.
3. **Validation sequence** — the end-to-end flow of one report.
4. **Data / knowledge model** — how information is stored and linked.

---

## 1. System Context Diagram

```mermaid
flowchart TB
    Citizen(["👤 Citizen"])
    Officer(["👮 Municipal Officer"])

    subgraph SYS["Incident Reporting Chatbot System"]
        Core["Chatbot + Validation + Case Engine"]
    end

    subgraph EXT["External Sources & Systems"]
        CCTV["🎥 Security Cameras / CCTV"]
        Sensors["📡 IoT Sensors (fill level, etc.)"]
        GIS["🗺️ GIS / Maps / Geocoding"]
        CMS["🗂️ Municipal Case Management (CRM/ERP)"]
        Notify["✉️ Notification (SMS/Email/Push)"]
    end

    Citizen -->|"chat + photo"| Core
    Core -->|"grounded answer, case ID"| Citizen
    Core -->|"validated case"| CMS
    Core -->|"status updates"| Notify --> Citizen
    Officer -->|"review flagged cases"| Core

    CCTV -.->|"corroborating imagery"| Core
    Sensors -.->|"telemetry"| Core
    GIS -.->|"location resolve / jurisdiction"| Core
    CMS -.->|"existing/duplicate cases"| Core
```

---

## 2. Component Architecture

The system is organized into five layers. Each box is an independently
replaceable component (see [03_how_to_modify.md](03_how_to_modify.md)).

```mermaid
flowchart TB
    subgraph CH["1 · Channel Layer"]
        Web["Web Widget"]
        WA["WhatsApp / Telegram"]
        Mobile["Mobile App"]
    end

    subgraph OR["2 · Orchestration Layer"]
        Gateway["API Gateway / BFF"]
        Dialog["Conversation Orchestrator<br/>(LLM + dialog state)"]
        Intent["Intent & Category Classifier"]
    end

    subgraph KN["3 · Knowledge & Reasoning Layer"]
        RAG["Retrieval / Grounding Service"]
        KG[("Knowledge Graph<br/>policies · departments · SLAs · past cases")]
        VDB[("Vector Store<br/>embeddings of docs & cases")]
    end

    subgraph VAL["4 · Validation Layer"]
        Ingest["Photo Ingest + EXIF/Geo extract"]
        CV["Computer Vision Service<br/>(YOLO detector / VLM verifier)"]
        Fusion["Evidence Fusion & Scoring<br/>(CV + location + external sources)"]
        Dedup["Duplicate / Jurisdiction Check"]
    end

    subgraph SV["5 · Services & Data Layer"]
        CaseSvc["Case Registration Service"]
        CMS["Case Management System"]
        Blob["Object Storage (photos/evidence)"]
        Ext["External Connectors<br/>CCTV · Sensors · GIS"]
        Audit["Audit / Event Log"]
    end

    Web & WA & Mobile --> Gateway --> Dialog
    Dialog --> Intent
    Dialog --> RAG --> KG
    RAG --> VDB
    Dialog --> Ingest --> CV --> Fusion
    Fusion --> Dedup
    Fusion --> Ext
    Dedup --> CaseSvc --> CMS
    Ingest --> Blob
    CaseSvc --> Audit
    Fusion --> KG
```

---

## 3. Validation Sequence (one incident, end-to-end)

```mermaid
sequenceDiagram
    autonumber
    actor U as Citizen
    participant C as Chatbot Orchestrator
    participant K as Knowledge Graph (RAG)
    participant V as CV Service (YOLO/VLM)
    participant F as Evidence Fusion
    participant X as External Sources
    participant R as Case Service
    participant M as Case Mgmt System

    U->>C: "There's trash overflowing here" + photo
    C->>K: classify + retrieve policy/department/SLA
    K-->>C: category=Trash, dept=Sanitation, SLA=24h, similar cases
    C-->>U: Grounded reply (what happens next, expected SLA)

    C->>V: analyze photo (detect objects / verify claim)
    V-->>C: label=garbage_overflow, conf=0.91, bbox[...]

    C->>F: {category, CV result, GPS/EXIF, timestamp}
    F->>X: fetch CCTV frame + sensor fill-level near location
    X-->>F: CCTV image, bin fill = 96%
    F->>V: verify corroborating CCTV frame
    V-->>F: garbage_overflow conf=0.87
    F-->>C: validation = AUTO_VALIDATED (score 0.89)

    alt Auto-validated (high confidence)
        C->>R: register case (+evidence bundle, score)
        R->>M: create ticket → routed to Sanitation
        M-->>R: caseId = MUN-2026-014823
        R-->>C: caseId
        C-->>U: "✅ Case MUN-2026-014823 registered. ETA 24h."
    else Needs review (medium)
        C->>R: register case flagged FOR_REVIEW
        C-->>U: "🟡 Logged; an officer will verify shortly."
    else Rejected (low / duplicate / out of jurisdiction)
        C-->>U: "❌ Could not validate: <reason>. Here's what to do…"
    end
```

---

## 4. Knowledge Graph Model

The knowledge graph is the "brain" that turns a free-text complaint into a
routable, policy-aware action and grounds the chatbot's answers.

```mermaid
erDiagram
    INCIDENT_TYPE ||--o{ CASE : classifies
    DEPARTMENT ||--o{ INCIDENT_TYPE : responsible_for
    DEPARTMENT ||--o{ SLA : defines
    INCIDENT_TYPE ||--o{ SLA : has
    LOCATION ||--o{ CASE : occurs_at
    LOCATION ||--o{ JURISDICTION : belongs_to
    CASE ||--o{ EVIDENCE : supported_by
    CASE ||--o{ CASE : duplicate_of
    POLICY ||--o{ INCIDENT_TYPE : governs

    INCIDENT_TYPE {
        string code
        string label
        string[] cv_labels
        float min_confidence
    }
    DEPARTMENT {
        string id
        string name
        string contact
    }
    SLA {
        string id
        int response_hours
        string priority
    }
    LOCATION {
        string geohash
        float lat
        float lon
        string zone
    }
    CASE {
        string id
        string status
        float validation_score
        datetime created_at
    }
    EVIDENCE {
        string id
        string type
        string uri
        float cv_confidence
    }
    POLICY {
        string id
        string title
        string text
    }
```

### How the layers map to concrete technology (example, swappable)

| Layer | Responsibility | Example tech (interchangeable) |
|-------|----------------|--------------------------------|
| Channel | Reach citizens | Web widget, WhatsApp Business API, Telegram |
| Orchestration | Dialog + routing | LLM (GPT/Claude/Llama) + LangGraph / Semantic Kernel |
| Intent classifier | Map text→category | Fine-tuned classifier or LLM function-calling |
| Knowledge graph | Grounding + routing | Neo4j / Azure Cosmos DB (Gremlin) / RDF store |
| Vector store | Semantic retrieval | pgvector / Azure AI Search / Pinecone |
| CV detector | Object detection | **YOLOv8/v11** (Ultralytics) |
| CV verifier | Claim verification | Vision-Language Model (GPT-4o / LLaVA / Florence-2) |
| Fusion & scoring | Combine signals | Rules + weighted score (or small ML model) |
| Case service | Register tickets | REST microservice |
| Case mgmt | System of record | ServiceNow / Dynamics 365 / custom |
| Storage | Evidence | S3 / Azure Blob |
| External | Corroboration | CCTV/VMS API, IoT hub, GIS/geocoder |

> The key idea: **each block talks through a defined interface**, so any one can
> be replaced without touching the others. See the next document for *why*.
