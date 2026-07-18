"""Tests for uploading a pre-built knowledge graph into the studio.

The GraphRAG engine persists to a JSON snapshot, so each test isolates state by
pointing ``STUDIO_DATA_DIR`` at a temp directory before importing the module.
Import is a pure graph operation (no Ollama/LLM), so these tests run offline.
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path))
    for mod in [m for m in sys.modules if m.startswith("studio_api")]:
        del sys.modules[mod]
    mod = importlib.import_module("studio_api.graphrag_engine")
    return mod.engine


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path))
    for mod in [m for m in sys.modules if m.startswith("studio_api")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient

    main = importlib.import_module("studio_api.main")
    return TestClient(main.app)


# --------------------------------------------------------------------------- #
# Sample graphs
# --------------------------------------------------------------------------- #
UNDERSTAND_ANYTHING = {
    "version": "1.0",
    "kind": "codebase",
    "project": {
        "name": "microservices-demo",
        "languages": ["go"],
        "frameworks": ["gRPC"],
        "description": "Online Boutique demo.",
        "analyzedAt": "2026-03-15",
        "gitCommitHash": "abc123",
    },
    "nodes": [
        {"id": "frontend", "type": "service", "name": "Frontend", "summary": "User-facing gateway.", "tags": ["go"], "complexity": "moderate"},
        {"id": "cart", "type": "service", "name": "Cart Service", "summary": "Manages the cart.", "tags": ["go"], "complexity": "simple"},
    ],
    "edges": [
        {"source": "frontend", "target": "cart", "type": "calls", "direction": "forward", "description": "gRPC call", "weight": 0.9},
    ],
    "layers": [],
    "tour": [],
}

GRAPHIFY = {
    "directed": True,
    "multigraph": False,
    "graph": {},
    "nodes": [
        {"id": "APIRouter", "label": "APIRouter", "file_type": "class", "summary": "Routes API requests.", "community": 0, "community_name": "APIRouter"},
        {"id": "Scope", "label": "Scope", "file_type": "class", "summary": "Request scope.", "community": 1},
    ],
    "links": [
        {"source": "APIRouter", "target": "Scope", "relation": "uses", "confidence": "EXTRACTED"},
    ],
    "hyperedges": [],
    "built_at_commit": "deadbeef",
}

AI_ATLAS = {
    "name": "AI Atlas",
    "version": "l1-l2",
    "nodes": [
        {"id": "ml", "name": "Machine Learning", "type": "concept", "description": "Learning from data."},
        {"id": "dl", "name": "Deep Learning", "type": "concept", "description": "Neural networks.", "parent": "ml"},
        {"id": "cnn", "name": "CNN", "type": "concept", "description": "Convolutional networks.", "parent": "dl"},
    ],
    "edges": [],
}


# --------------------------------------------------------------------------- #
# Engine-level tests
# --------------------------------------------------------------------------- #
def test_import_understand_anything_autodetect(engine):
    result = engine.import_graph(UNDERSTAND_ANYTHING, fmt="auto")
    assert result["format"] == "understand_anything"
    assert result["title"] == "microservices-demo"
    assert result["entities_added"] == 2
    assert result["relationships_added"] == 1

    graph = engine.graph()
    assert graph["stats"]["entities"] == 2
    assert graph["stats"]["relationships"] == 1
    node = next(n for n in graph["nodes"] if n["name"] == "Frontend")
    assert node["source_type"] == "curated"
    assert node["origin"]["origin_id"] == "frontend"
    assert node["origin"]["origin_version"] == "abc123"


def test_import_graphify_autodetect(engine):
    result = engine.import_graph(GRAPHIFY, fmt="auto")
    assert result["format"] == "graphify"
    assert result["entities_added"] == 2
    assert result["relationships_added"] == 1
    graph = engine.graph()
    edge = graph["edges"][0]
    assert edge["description"] == "uses"
    assert edge["source_type"] == "curated"


def test_import_ai_atlas_hierarchy_synthesizes_edges(engine):
    result = engine.import_graph(AI_ATLAS, fmt="ai_atlas")
    assert result["entities_added"] == 3
    # parent links become categorized_under edges (dl->ml, cnn->dl)
    assert result["relationships_added"] == 2
    graph = engine.graph()
    descriptions = {e["description"] for e in graph["edges"]}
    assert descriptions == {"categorized_under"}


def test_preserve_curated_not_overwritten_by_extracted(engine):
    engine.import_graph(
        {"nodes": [{"id": "a", "name": "Alice", "description": "Curated bio."}], "edges": []},
        fmt="generic",
        source_type="curated",
    )
    # An extracted upsert of the same entity must not overwrite curated data.
    engine.import_graph(
        {"nodes": [{"id": "a", "name": "Alice", "description": "Extracted-longer-bio-that-is-clearly-bigger."}], "edges": []},
        fmt="generic",
        source_type="extracted",
        merge_strategy="preserve_curated",
    )
    node = next(n for n in engine.graph()["nodes"] if n["name"] == "Alice")
    assert node["source_type"] == "curated"
    assert node["description"] == "Curated bio."


def test_overwrite_strategy_replaces_fields(engine):
    engine.import_graph(
        {"nodes": [{"id": "a", "name": "Alice", "description": "Old."}], "edges": []},
        fmt="generic",
        source_type="curated",
    )
    engine.import_graph(
        {"nodes": [{"id": "a", "name": "Alice", "description": "New."}], "edges": []},
        fmt="generic",
        source_type="inferred",
        merge_strategy="overwrite",
    )
    node = next(n for n in engine.graph()["nodes"] if n["name"] == "Alice")
    assert node["description"] == "New."
    assert node["source_type"] == "inferred"


def test_import_empty_graph_raises(engine):
    with pytest.raises(ValueError):
        engine.import_graph({"nodes": [], "edges": []}, fmt="generic")


def test_import_bad_source_type_raises(engine):
    with pytest.raises(ValueError):
        engine.import_graph(GRAPHIFY, source_type="bogus")


# --------------------------------------------------------------------------- #
# API-level tests
# --------------------------------------------------------------------------- #
def test_import_endpoint(client):
    resp = client.post(
        "/graphrag/import",
        json={"graph": UNDERSTAND_ANYTHING, "format": "auto", "source_type": "curated"},
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["entities_added"] == 2

    graph = client.get("/graphrag/graph").json()
    assert graph["stats"]["entities"] == 2


def test_export_endpoint_roundtrip(client):
    client.post("/graphrag/import", json={"graph": GRAPHIFY, "format": "graphify"})
    export = client.get("/graphrag/export").json()
    assert export["stats"]["entities"] == 2
    assert len(export["entities"]) == 2
    assert len(export["relationships"]) == 1
    # Provenance is preserved in the export.
    assert all(e["source_type"] == "curated" for e in export["entities"].values())


def test_import_endpoint_rejects_bad_format(client):
    resp = client.post("/graphrag/import", json={"graph": GRAPHIFY, "format": "nope"})
    assert resp.status_code == 400
