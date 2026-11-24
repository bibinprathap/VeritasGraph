"""Automated and set-based metrics for the RAG evaluation harness.

These are pure functions ``(prediction, gold) -> float`` so they can be unit
tested with no LLM, no network, and no Ollama. The HotpotQA normalisation and
token-F1 follow the standard SQuAD/HotpotQA evaluation convention.

Judge-based metrics (comprehensiveness, diversity, citation faithfulness) live in
``eval.rag.judge`` because they require an LLM; everything here is deterministic.
"""

from __future__ import annotations

import re
import statistics
import string
from collections import Counter
from typing import Dict, Iterable, List, Sequence

# --------------------------------------------------------------------------- #
# Text normalisation (HotpotQA / SQuAD convention)
# --------------------------------------------------------------------------- #
_ARTICLES = re.compile(r"\b(a|an|the)\b", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_answer(text: str) -> str:
    """Lowercase, remove punctuation, articles, and collapse whitespace."""
    if text is None:
        return ""
    text = text.lower()
    text = text.translate(_PUNCT_TABLE)
    text = _ARTICLES.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def _tokens(text: str) -> List[str]:
    norm = normalize_answer(text)
    return norm.split() if norm else []


# --------------------------------------------------------------------------- #
# QA metrics (Task 2 — HotpotQA)
# --------------------------------------------------------------------------- #
def exact_match(prediction: str, gold: str) -> float:
    """1.0 if the normalised strings are identical, else 0.0."""
    return 1.0 if normalize_answer(prediction) == normalize_answer(gold) else 0.0


def token_f1(prediction: str, gold: str) -> float:
    """Token-level F1 between prediction and gold (HotpotQA convention)."""
    pred_tokens = _tokens(prediction)
    gold_tokens = _tokens(gold)

    # Edge cases: if either side is empty, F1 is 1.0 only when both are empty.
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0

    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


# --------------------------------------------------------------------------- #
# Citation metrics (Task 3 — attribution vs HotpotQA supporting facts)
# --------------------------------------------------------------------------- #
def citation_precision(cited: Iterable[str], gold: Iterable[str]) -> float:
    """Fraction of cited sources that are in the gold supporting set.

    If nothing was cited, precision is 0.0 (the system failed to attribute).
    """
    cited_set = set(cited)
    gold_set = set(gold)
    if not cited_set:
        return 0.0
    return len(cited_set & gold_set) / len(cited_set)


def citation_recall(cited: Iterable[str], gold: Iterable[str]) -> float:
    """Fraction of gold supporting sources that were cited.

    If there is no gold set, recall is 1.0 (nothing to recover) only when the
    system also cited nothing; otherwise 0.0 would be misleading — we define the
    empty-gold case as 1.0 to avoid penalising unanswerable-by-design items.
    """
    cited_set = set(cited)
    gold_set = set(gold)
    if not gold_set:
        return 1.0
    return len(cited_set & gold_set) / len(gold_set)


def citation_f1(cited: Iterable[str], gold: Iterable[str]) -> float:
    """Harmonic mean of citation precision and recall."""
    cited_list = list(cited)
    gold_list = list(gold)
    p = citation_precision(cited_list, gold_list)
    r = citation_recall(cited_list, gold_list)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# --------------------------------------------------------------------------- #
# Aggregation (mean +/- std over per-query scores and seeds)
# --------------------------------------------------------------------------- #
def aggregate(scores: Sequence[float]) -> Dict[str, float]:
    """Return ``{"mean", "std", "n"}`` for a list of per-item scores."""
    values = [float(s) for s in scores]
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "n": 0}
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if n > 1 else 0.0
    return {"mean": mean, "std": std, "n": n}


def mean_over_seeds(per_seed_means: Sequence[float]) -> Dict[str, float]:
    """Aggregate seed-level means into a reported ``mean +/- std``.

    Uses the sample standard deviation across seeds (the spread we report in the
    paper tables as mean +/- std over >=3 seeds).
    """
    values = [float(v) for v in per_seed_means]
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "n": 0}
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if n > 1 else 0.0
    return {"mean": mean, "std": std, "n": n}
