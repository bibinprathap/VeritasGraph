"""FastAPI endpoint tests using the ASGI test client."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from clinical_kg.api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        c.post("/reset")
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_load_samples_and_query(client):
    r = client.post("/demo/load-samples")
    assert r.status_code == 200
    assert r.json()["loaded"] == 4

    r = client.post(
        "/query",
        json={"query": "patients with T2DM taking metformin whose most recent eGFR < 30"},
    )
    body = r.json()
    assert body["match_count"] == 2
    ids = {m["patient_id"] for m in body["matches"]}
    assert ids == {"P001", "P004"}
    assert all(m["citations"] for m in body["matches"])


def test_ingest_endpoint_redacts_and_reconciles(client):
    r = client.post(
        "/ingest",
        json={
            "notes": [
                {
                    "doc_id": "n1",
                    "patient_id": "PX",
                    "text": "HPI: denies diabetes.\nProblem List: Type 2 diabetes mellitus on metformin 500mg BID.\nMRN: 1234567",
                }
            ]
        },
    )
    body = r.json()["ingested"][0]
    assert body["phi_redactions"] >= 1
    assert body["contradictions"]


def test_contradictions_endpoint(client):
    client.post("/demo/load-samples")
    r = client.get("/contradictions")
    assert r.status_code == 200
    assert any(c["code"] == "44054006" for c in r.json()["contradictions"])


def test_graph_endpoint(client):
    client.post("/demo/load-samples")
    r = client.get("/graph", params={"patient_id": "P001"})
    body = r.json()
    assert body["nodes"]
    assert body["edges"]


def test_k_anonymity_endpoint(client):
    r = client.post(
        "/risk/k-anonymity",
        json={
            "records": [
                {"zip3": "021", "age_band": "60-70"},
                {"zip3": "021", "age_band": "60-70"},
            ],
            "quasi_identifiers": ["zip3", "age_band"],
            "target_k": 2,
        },
    )
    body = r.json()
    assert body["k"] == 2
    assert body["satisfied"] is True
