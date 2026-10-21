"""Observability / SRE layer (paper §3.5).

Lightweight tracing + metrics. In production this delegates to ``future-agi``
(OpenTelemetry-native). Here it records spans and counters in-memory so tests can
assert that every request is observable and safety events are counted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Span:
    name: str
    start: float
    end: float | None = None
    attributes: Dict[str, str] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end is None:
            return 0.0
        return (self.end - self.start) * 1000.0


class Observability:
    def __init__(self) -> None:
        self.spans: List[Span] = []
        self.counters: Dict[str, int] = {}

    def start_span(self, name: str, **attrs: str) -> Span:
        span = Span(name=name, start=time.perf_counter(), attributes=dict(attrs))
        self.spans.append(span)
        return span

    def end_span(self, span: Span) -> None:
        span.end = time.perf_counter()

    def incr(self, counter: str, by: int = 1) -> None:
        self.counters[counter] = self.counters.get(counter, 0) + by

    def metric(self, counter: str) -> int:
        return self.counters.get(counter, 0)
