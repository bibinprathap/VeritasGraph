"""TC-10 — Reproducibility: seed-fixed deterministic fields are stable.

Reviewer R2-1/R2-5: results must be reproducible from a published seed. We
assert that re-running the harness reproduces the deterministic fields
(quality, citations, authorization, audit, security intervals) exactly, while
*excluding* wall-clock latency which is legitimately non-deterministic.
"""

from __future__ import annotations

from medtrust.benchmark import evaluate
from medtrust.eval.attacks import run_all


DETERMINISTIC_METRICS = (
    "accuracy", "hallucination", "citations_enforced", "unauthorized_blocked",
)


def _strip_latency(report: dict) -> dict:
    """Drop wall-clock latency so only deterministic fields are compared."""
    out = {
        "trials": report["trials"],
        "base_seed": report["base_seed"],
        "audit_tamper_detected": report["audit_tamper_detected"],
        "n_scenarios": report["n_scenarios"],
        "categories": report["categories"],
        "configs": {},
    }
    for key, cfg in report["configs"].items():
        out["configs"][key] = {
            m: cfg["metrics"][m] for m in DETERMINISTIC_METRICS
        }
        out["configs"][key]["security_wilson"] = cfg["security_wilson"]
    return out


def test_benchmark_deterministic_fields_are_stable():
    a = _strip_latency(evaluate(trials=10, base_seed=7))
    b = _strip_latency(evaluate(trials=10, base_seed=7))
    assert a == b, "seed-fixed deterministic fields drifted between runs"


def test_security_eval_is_fully_deterministic():
    a = run_all()
    b = run_all()
    assert a == b, "security evaluation is not reproducible under fixed corpus"


def test_known_headline_numbers_hold():
    """Guard the specific numbers the paper publishes (seed 7)."""
    r = evaluate(trials=30, base_seed=7)
    mt = r["configs"]["MT"]["metrics"]
    b0 = r["configs"]["B0"]["metrics"]
    # measured control metrics are exact
    assert mt["unauthorized_blocked"]["mean"] == 1.0
    assert mt["citations_enforced"]["mean"] == 1.0
    assert b0["unauthorized_blocked"]["mean"] == 0.0
    assert b0["citations_enforced"]["mean"] == 0.0
    assert r["audit_tamper_detected"] is True
    # illustrative quality within a tight tolerance of the published values
    assert abs(mt["accuracy"]["mean"] - 0.795) < 0.01
    assert abs(mt["hallucination"]["mean"] - 0.071) < 0.01
    assert r["n_scenarios"] == 40
    assert len(r["categories"]) == 6
