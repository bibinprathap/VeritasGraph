"""Token-budgeted context selection for the Knowledge section.

When a knowledge source returns more text than a model's context window can
afford, this helper keeps the highest-signal chunks within a token budget and
hands everything it drops to headroom's CCR store, so the dropped material can
still be retrieved on demand. This is the "lossy on the wire, lossless
end-to-end" contract: the prompt only carries the kept chunks plus a
``<<ccr:HASH>>`` marker per dropped chunk, and the original bytes are recovered
by resolving that hash. Token counting uses a pluggable callable and falls back
to a whitespace word count.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

from studio_api.ccr import InMemoryCcrStore, compute_key, marker_for

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _default_token_counter(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _query_terms(query: str) -> set:
    return {t.lower() for t in _WORD_RE.findall(query)}


def _score(chunk: str, terms: set) -> float:
    words = [w.lower() for w in _WORD_RE.findall(chunk)]
    if not words:
        return 0.0
    if not terms:
        # No query: prefer denser/shorter chunks so the budget covers more items.
        return 1.0 / (1.0 + len(words))
    overlap = sum(1 for w in words if w in terms)
    density = overlap / len(words)
    return overlap + density


@dataclass
class BudgetResult:
    """Outcome of a budgeting pass."""

    kept: List[str] = field(default_factory=list)
    dropped_handles: List[str] = field(default_factory=list)
    markers: List[str] = field(default_factory=list)
    used_tokens: int = 0
    budget_tokens: int = 0

    @property
    def dropped_count(self) -> int:
        return len(self.dropped_handles)


class ContextBudgeter:
    """Selects chunks within a token budget and stashes dropped chunks in CCR."""

    def __init__(
        self,
        token_counter: Optional[Callable[[str], int]] = None,
        store: Optional[InMemoryCcrStore] = None,
    ) -> None:
        self._count = token_counter or _default_token_counter
        # headroom CCR store: content-addressed, TTL + capacity bounded.
        self._store = store or InMemoryCcrStore()

    def budget(
        self,
        chunks: Sequence[str],
        *,
        query: str = "",
        max_tokens: int = 1024,
    ) -> BudgetResult:
        """Keep the highest-scoring chunks that fit within ``max_tokens``."""
        terms = _query_terms(query)
        ordered = sorted(
            (c for c in chunks if c and c.strip()),
            key=lambda c: _score(c, terms),
            reverse=True,
        )

        result = BudgetResult(budget_tokens=max_tokens)
        for chunk in ordered:
            cost = self._count(chunk)
            if result.used_tokens + cost <= max_tokens:
                result.kept.append(chunk)
                result.used_tokens += cost
            else:
                # Drop from the prompt but stash in CCR keyed by its hash.
                handle = compute_key(chunk)
                self._store.put(handle, chunk)
                result.dropped_handles.append(handle)
                result.markers.append(marker_for(handle))
        return result

    def retrieve(self, handle: str) -> Optional[str]:
        """Resolve a dropped chunk by its CCR handle."""
        return self._store.get(handle)


# Module-level instance shared by the knowledge controller.
budgeter = ContextBudgeter()
