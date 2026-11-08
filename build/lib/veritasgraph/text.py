"""Text helpers shared by the engine, answerability and compile stages."""

from __future__ import annotations

import re
from typing import List

# Question words that say nothing about which entity is meant.
STOPWORDS = frozenset(
    {
        "what", "which", "where", "when", "does", "about", "with", "from",
        "that", "this", "there", "their", "have", "into", "between", "explain",
        "describe", "tell", "show", "list", "many", "much", "should", "would",
        "could", "they", "them", "were", "been", "being", "whom", "whose",
        "why", "how", "the", "and", "are", "was", "who", "for", "any", "all",
        "some", "other", "than", "then", "also", "only", "over", "under",
    }
)


def norm(name: str) -> str:
    """Lower-case and collapse whitespace (entity de-duplication key)."""
    return re.sub(r"\s+", " ", name or "").strip().lower()


def query_tokens(text: str) -> List[str]:
    """Content words of a question (no stopwords, nothing of 3 chars or fewer)."""
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 3 and t not in STOPWORDS]
