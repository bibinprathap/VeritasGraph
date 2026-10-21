"""TC-23 — Interval math edge cases (Wilson / bootstrap).

These feed the published confidence intervals, so the boundary behaviour at
n=0, p=0, p=1 and the exact intervals the paper reports must be well-defined.
"""

from __future__ import annotations

from medtrust.eval.stats import wilson, bootstrap_ci, Interval


def test_wilson_zero_n_is_defined():
    iv = wilson(0, 0)
    assert iv.n == 0
    assert 0.0 <= iv.low <= iv.high <= 1.0


def test_wilson_all_success_upper_is_one_lower_below_one():
    iv = wilson(14, 14)          # injection one-shot block
    assert iv.mean == 1.0
    assert iv.high == 1.0
    assert iv.low < 1.0
    # published value [78.5, 100]
    assert abs(iv.low - 0.785) < 0.01


def test_wilson_all_failure_lower_is_zero():
    iv = wilson(0, 8)            # false-denial rate
    assert iv.mean == 0.0
    assert iv.low == 0.0
    assert iv.high > 0.0
    assert abs(iv.high - 0.324) < 0.01  # published [0, 32.4]


def test_wilson_conformance_interval_matches_paper():
    iv = wilson(50, 50)         # IAM conformance
    assert iv.mean == 1.0
    assert abs(iv.low - 0.929) < 0.01   # published [92.9, 100]


def test_wilson_bounds_always_within_unit_interval():
    for s, n in [(1, 3), (3, 3), (7, 10), (12, 12), (1, 100)]:
        iv = wilson(s, n)
        assert 0.0 <= iv.low <= iv.mean <= iv.high <= 1.0


def test_bootstrap_ci_degenerate_inputs():
    assert bootstrap_ci([]).n == 0
    one = bootstrap_ci([0.5])
    assert one.mean == 0.5 and one.low == 0.5 and one.high == 0.5


def test_bootstrap_ci_all_equal_has_zero_width():
    iv = bootstrap_ci([1.0, 1.0, 1.0, 1.0], seed=1)
    assert iv.low == 1.0 and iv.high == 1.0


def test_interval_pct_formats_percentages():
    assert Interval(1.0, 0.785, 1.0, 14).pct() == "100.0% [78.5, 100.0]"
