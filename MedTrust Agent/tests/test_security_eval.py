"""Tests for the adversarial security evaluation (reviewer R2-2)."""

from medtrust.eval.attacks import (
    run_injection_benchmark, run_adaptive_attack, run_false_denial_probe,
    run_conformance_check, PI_CORPUS,
)
from medtrust.eval.stats import wilson, bootstrap_ci


def test_injection_benchmark_blocks_known_payloads():
    r = run_injection_benchmark()
    # Known, unobfuscated payloads are fully blocked one-shot.
    assert r["overall"]["mean"] == 1.0
    assert r["overall"]["n"] == sum(1 for p in PI_CORPUS if p.should_block)


def test_adaptive_attack_reveals_filter_weakness():
    r = run_adaptive_attack(rounds=3)
    # Round 1 blocks base payloads; later rounds expose substring-filter evasion.
    assert r["history"][0]["bypassed"] == 0
    assert r["max_bypass_rate"]["mean"] > 0.0  # adaptive obfuscation evades


def test_false_denial_rate_is_low():
    r = run_false_denial_probe()
    # Benign-but-tricky legitimate requests should not be wrongly blocked.
    assert r["false_denial_rate"]["mean"] == 0.0
    assert r["n"] >= 8


def test_conformance_full_match():
    r = run_conformance_check()
    assert r["conformance_rate"]["mean"] == 1.0
    assert r["mismatches"] == []
    assert r["cases"] >= 25  # roles x actions x step-up enumerated


def test_wilson_interval_bounds():
    iv = wilson(10, 10)
    assert iv.mean == 1.0 and iv.low < 1.0 and iv.high == 1.0
    iv2 = wilson(0, 10)
    assert iv2.mean == 0.0 and iv2.high > 0.0


def test_bootstrap_ci_mean():
    iv = bootstrap_ci([1.0, 1.0, 1.0, 1.0])
    assert iv.mean == 1.0
    iv2 = bootstrap_ci([0.0, 1.0, 0.0, 1.0], seed=1)
    assert 0.0 <= iv2.low <= iv2.mean <= iv2.high <= 1.0
