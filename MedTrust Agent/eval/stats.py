"""Statistics helpers for interval estimation over independent cases.

Reviewer R2-2 asks for *interval estimates based on independent cases* for the
security rates (block rate, false-denial rate). For a binomial proportion the
Wilson score interval is preferred over the normal approximation at the
extreme rates (0 or 1) we frequently observe.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class Interval:
    mean: float
    low: float
    high: float
    n: int

    def as_dict(self) -> dict:
        return {"mean": self.mean, "low": self.low, "high": self.high, "n": self.n}

    def pct(self) -> str:
        return f"{self.mean*100:.1f}% [{self.low*100:.1f}, {self.high*100:.1f}]"


def wilson(successes: int, n: int, z: float = 1.96) -> Interval:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if n == 0:
        return Interval(0.0, 0.0, 0.0, 0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return Interval(p, max(0.0, center - half), min(1.0, center + half), n)


def bootstrap_ci(values: Sequence[float], iters: int = 2000, z: float = 1.96,
                 seed: int = 0) -> Interval:
    """Percentile bootstrap CI for the mean of per-case values."""
    vals = list(values)
    n = len(vals)
    if n == 0:
        return Interval(0.0, 0.0, 0.0, 0)
    if n == 1:
        return Interval(vals[0], vals[0], vals[0], 1)
    rng = random.Random(seed)
    means: List[float] = []
    for _ in range(iters):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[int(0.975 * iters) - 1]
    return Interval(sum(vals) / n, lo, hi, n)
