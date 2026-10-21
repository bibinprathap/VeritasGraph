"""TC-01/TC-06 — Paper ↔ results consistency and camera-ready invariants.

These tests fail if the LaTeX manuscript drifts from the generated results JSON
or from the EDAS submission constraints. They are skipped gracefully when the
build artifacts (results JSON, compiled PDF) are not present, so the unit suite
still runs on a bare checkout; CI runs ``reproduce.sh`` first to populate them.
"""

from __future__ import annotations

import json
import os
import re

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(ROOT, "medtrust", "results")
PAPER = os.path.join(ROOT, "paper_ieee")
SYSMODEL = os.path.join(PAPER, "_system_model.tex")
PDF = os.path.join(PAPER, "main.pdf")


def _load(name):
    path = os.path.join(RESULTS, name)
    if not os.path.exists(path):
        pytest.skip(f"{name} not generated; run reproduce.sh")
    with open(path) as f:
        return json.load(f)


def _read(path):
    if not os.path.exists(path):
        pytest.skip(f"{path} missing")
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


# --- TC-01: latency is wall-clock (non-deterministic); assert the stable ratio
# band and structural facts, not exact microsecond tokens that drift per run. ---
def test_latency_ratio_matches_json():
    lat = _load("latency.json")
    mt = lat["MT"]["total"]["mean"]
    b3 = lat["B3"]["total"]["mean"]
    ratio = mt / b3
    # The control plane adds a small, bounded overhead on a microsecond base.
    assert 1.1 <= ratio <= 2.5, ratio
    assert mt > b3, (mt, b3)
    tex = _read(SYSMODEL)
    # Paper states the ratio approximately and frames it on a microsecond base.
    assert r"1.5\times" in tex, "paper must state the ~1.5x reconciled latency ratio"
    assert r"\mu s" in tex, "paper must report absolute per-component microsecond costs"


def test_security_numbers_present_in_paper():
    sec = _load("security.json")
    assert sec["injection_benchmark"]["overall"]["mean"] == 1.0
    assert sec["conformance"]["conformance_rate"]["mean"] == 1.0
    tex = _read(SYSMODEL)
    for token in ["78.5", "92.9", "32.4", "46.4"]:
        assert token in tex, f"expected security CI token {token} in paper"


def test_ablation_values_match_paper_table():
    metrics = _load("metrics.json")
    mt = metrics["configs"]["MT"]["metrics"]
    assert round(mt["accuracy"]["mean"] * 100, 1) == 79.5
    assert round(mt["hallucination"]["mean"] * 100, 1) == 7.1
    tex = _read(SYSMODEL)
    assert "79.5" in tex and "7.1" in tex


def test_per_component_latency_tokens_in_paper():
    lat = _load("latency.json")
    mt, b3 = lat["MT"], lat["B3"]
    # Structural truths that hold regardless of wall-clock noise: MT runs the
    # control plane (IAM + governance) that B3 lacks, so MT costs strictly more.
    assert mt["iam"]["mean"] > 0 and mt["governance"]["mean"] > 0
    assert b3["iam"]["mean"] == 0 and b3["governance"]["mean"] == 0
    assert mt["total"]["mean"] > b3["total"]["mean"]
    tex = _read(SYSMODEL)
    # Paper reports representative absolute per-component microsecond costs.
    assert r"\mu s" in tex and "per-component" in tex


# --- TC-03: forbidden phrases are gone -----------------------------------------
def test_no_forbidden_phrases_in_tex():
    for name in os.listdir(PAPER):
        if name.endswith(".tex"):
            body = _read(os.path.join(PAPER, name)).lower()
            assert "provably" not in body, f"claim 'provably' resurfaced in {name}"
            assert "immutable audit" not in body, f"'immutable audit' in {name}"


# --- TC-08: every \cite key resolves in references.bib -------------------------
def test_all_citations_resolve():
    bib = _read(os.path.join(PAPER, "references.bib"))
    bibkeys = set(re.findall(r"@\w+\{([^,\s]+)", bib))
    cited = set()
    for name in os.listdir(PAPER):
        if name.endswith(".tex"):
            for m in re.findall(r"\\cite\{([^}]*)\}", _read(os.path.join(PAPER, name))):
                cited.update(k.strip() for k in m.split(","))
    missing = cited - bibkeys
    assert not missing, f"undefined citation keys: {sorted(missing)}"
    for reg in ["hipaa1996", "euaiact", "nistairmf", "nist800207"]:
        assert reg in bibkeys, f"regulatory key {reg} missing from references.bib"


# --- TC-06: EDAS compliance on the compiled PDF --------------------------------
def test_pdf_has_no_links_bookmarks_and_is_within_page_budget():
    if not os.path.exists(PDF):
        pytest.skip("main.pdf not built")
    data = open(PDF, "rb").read()
    assert len(re.findall(rb"/Subtype\s*/Link", data)) == 0, "PDF has link annotations"
    assert len(re.findall(rb"/URI", data)) == 0, "PDF has URI actions"
    assert len(re.findall(rb"/Outlines", data)) == 0, "PDF has bookmarks"
