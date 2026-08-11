"""FastAPI service exposing the clinical knowledge-graph pipeline.

Endpoints
---------
GET  /health                  -> service status
POST /ingest                  -> ingest one or more clinical notes
POST /query                   -> natural-language cohort query
GET  /patients                -> list ingested patients + facts
GET  /contradictions          -> reconciliation contradictions
GET  /interactions            -> drug-drug interaction flags (all or per-patient)
GET  /graph                   -> cytoscape graph (optionally per-patient)
POST /risk/k-anonymity        -> k-anonymity of a released cohort
POST /reset                   -> clear the in-memory graph
POST /demo/load-samples       -> load bundled synthetic notes
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import Document
from .pipeline import Pipeline
from .risk import k_anonymity
from .sample_data import SAMPLE_DOCUMENTS

app = FastAPI(title="Clinical Knowledge Graph API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single in-process pipeline (demo scope). Swap for per-session in production.
pipeline = Pipeline()


class NoteIn(BaseModel):
    doc_id: str
    patient_id: str
    text: str
    encounter_date: str | None = None
    encounter_type: str = "note"


class IngestIn(BaseModel):
    notes: list[NoteIn]


class QueryIn(BaseModel):
    query: str


class KAnonIn(BaseModel):
    records: list[dict]
    quasi_identifiers: list[str]
    target_k: int = 5


def _assertion_dict(a) -> dict:
    return {
        "system": a.concept.system,
        "code": a.concept.code,
        "display": a.concept.display,
        "label": a.label,
        "negation": a.negation,
        "certainty": a.certainty,
        "temporality": a.temporality,
        "experiencer": a.experiencer,
        "contradiction": a.contradiction,
        "attributes": a.attributes,
        "citations": sorted({s.citation() for s in a.evidence}),
        "conflicting_spans": [
            {"section": s.section, "text": s.text, "citation": s.citation()}
            for s in a.conflicting_spans
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "stats": pipeline.stats()}


@app.post("/ingest")
def ingest(payload: IngestIn) -> dict:
    results = []
    for note in payload.notes:
        r = pipeline.ingest(
            Document(
                doc_id=note.doc_id,
                patient_id=note.patient_id,
                text=note.text,
                encounter_date=note.encounter_date,
                encounter_type=note.encounter_type,
            )
        )
        results.append(
            {
                "doc_id": r.doc_id,
                "patient_id": r.patient_id,
                "phi_redactions": r.replacements,
                "vault_id": r.vault_id,
                "assertions": [_assertion_dict(a) for a in r.assertions],
                "contradictions": [_assertion_dict(a) for a in r.contradictions],
            }
        )
    return {"ingested": results, "stats": pipeline.stats()}


@app.post("/query")
def query(payload: QueryIn) -> dict:
    from . import query as query_mod

    parsed = query_mod.parse_query(payload.query)
    matches = pipeline.query(payload.query)
    return {
        "query": payload.query,
        "parsed": {
            "conditions": parsed.conditions,
            "medications": parsed.medications,
            "procedures": parsed.procedures,
            "lab_filters": [asdict(f) for f in parsed.lab_filters],
        },
        "match_count": len(matches),
        "matches": [
            {"patient_id": m.patient_id, "reasons": m.reasons, "citations": m.citations}
            for m in matches
        ],
    }


@app.get("/patients")
def patients() -> dict:
    ids = sorted({r.patient_id for r in pipeline.ingested})
    return {
        "patients": [
            {"patient_id": pid, "facts": pipeline.kg.facts_for(pid)} for pid in ids
        ]
    }


@app.get("/contradictions")
def contradictions() -> dict:
    out = []
    for r in pipeline.ingested:
        for a in r.contradictions:
            out.append({"patient_id": r.patient_id, "doc_id": r.doc_id, **_assertion_dict(a)})
    return {"contradictions": out}


@app.get("/interactions")
def interactions(patient_id: str | None = None) -> dict:
    flags = pipeline.interactions(patient_id)
    return {"patient_id": patient_id, "count": len(flags), "interactions": flags}


@app.get("/graph")
def graph(patient_id: str | None = None) -> dict:
    return pipeline.kg.cytoscape(patient_id)


@app.post("/risk/k-anonymity")
def risk_k_anonymity(payload: KAnonIn) -> dict:
    report = k_anonymity(payload.records, payload.quasi_identifiers, payload.target_k)
    return asdict(report)


@app.post("/reset")
def reset() -> dict:
    global pipeline
    pipeline = Pipeline()
    return {"status": "reset", "stats": pipeline.stats()}


@app.post("/demo/load-samples")
def load_samples() -> dict:
    global pipeline
    pipeline = Pipeline()
    pipeline.ingest_all(SAMPLE_DOCUMENTS)
    return {
        "loaded": len(SAMPLE_DOCUMENTS),
        "stats": pipeline.stats(),
    }
