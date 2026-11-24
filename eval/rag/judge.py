"""LLM-as-judge for metrics that cannot be computed deterministically.

Covers Task 1 (Comprehensiveness, Diversity) and the faithfulness component of
Task 3 (does the answer genuinely derive from a cited source, or is it
post-rationalised?). Every judge returns a float in ``[0, 1]``.

The judge LLM is injected (``chat``) so these functions are fully unit-testable
with a fake. Parsing is defensive: a strict-JSON score is expected, we retry
once, and fall back to extracting the first number in ``[0, 1]`` before giving
up and raising.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List

from .contract import Answer
from .llm import ChatFn, ollama_chat

_SCORE_RE = re.compile(r"-?\d*\.?\d+")


@dataclass(frozen=True)
class JudgeResult:
    score: float
    raw: str


def _parse_score(text: str) -> float:
    """Extract a 0..1 score from a judge response (JSON first, then a number)."""
    if not text:
        raise ValueError("empty judge response")
    # Prefer strict JSON {"score": x}.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "score" in obj:
            return _clamp(float(obj["score"]))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    # Fall back: first number in the text.
    m = _SCORE_RE.search(text)
    if not m:
        raise ValueError(f"no numeric score found in judge response: {text!r}")
    return _clamp(float(m.group()))


def _clamp(value: float) -> float:
    # Tolerate a 0..10 integer rubric (e.g. "8" -> 0.8) but NOT fractional
    # over-ranges like 1.5, which should simply clamp to 1.0.
    if 1.0 < value <= 10.0 and float(value).is_integer():
        value = value / 10.0
    return max(0.0, min(1.0, value))


def _judge(
    prompt_messages: List[Dict[str, str]],
    *,
    model: str,
    temperature: float,
    chat: ChatFn,
) -> JudgeResult:
    raw = chat(model, prompt_messages, temperature)
    try:
        return JudgeResult(score=_parse_score(raw), raw=raw)
    except ValueError:
        # One retry with an explicit format reminder.
        retry = list(prompt_messages) + [
            {
                "role": "user",
                "content": 'Respond with STRICT JSON only: {"score": <0..1 float>}.',
            }
        ]
        raw2 = chat(model, retry, temperature)
        return JudgeResult(score=_parse_score(raw2), raw=raw2)


_RUBRIC_SYSTEM = (
    "You are a strict evaluation judge. You score a candidate answer on a single "
    "criterion. Respond with STRICT JSON only: {\"score\": <float between 0 and 1>}. "
    "Do not add any prose."
)


def comprehensiveness(
    question: str,
    answer: Answer,
    *,
    model: str,
    temperature: float = 0.0,
    chat: ChatFn = ollama_chat,
) -> float:
    """How much detail the answer provides to cover all aspects of the question."""
    user = (
        "Criterion: COMPREHENSIVENESS — how much detail does the answer provide to "
        "cover all aspects and implications of the question?\n\n"
        f"QUESTION: {question}\n\nANSWER: {answer['answer']}"
    )
    return _judge(
        [{"role": "system", "content": _RUBRIC_SYSTEM}, {"role": "user", "content": user}],
        model=model,
        temperature=temperature,
        chat=chat,
    ).score


def diversity(
    question: str,
    answer: Answer,
    *,
    model: str,
    temperature: float = 0.0,
    chat: ChatFn = ollama_chat,
) -> float:
    """Variety and richness of perspectives in the answer (avoids repetition)."""
    user = (
        "Criterion: DIVERSITY — the variety and richness of perspectives the answer "
        "provides. Penalise repetition and single-angle answers.\n\n"
        f"QUESTION: {question}\n\nANSWER: {answer['answer']}"
    )
    return _judge(
        [{"role": "system", "content": _RUBRIC_SYSTEM}, {"role": "user", "content": user}],
        model=model,
        temperature=temperature,
        chat=chat,
    ).score


def citation_faithfulness(
    answer: Answer,
    *,
    model: str,
    temperature: float = 0.0,
    chat: ChatFn = ollama_chat,
) -> float:
    """Does the answer genuinely derive from its cited sources (not post-hoc)?

    The judge is shown the answer and the exact text of the sources it cited and
    must decide whether the cited text actually supports the claims.
    """
    cited_text = "\n\n".join(
        f"[{c['id']}] {c['title']}: {c['text']}" for c in answer["citations"]
    )
    if not cited_text:
        return 0.0
    user = (
        "Criterion: CITATION FAITHFULNESS — do the cited sources genuinely support "
        "the claims in the answer? Score 1.0 if every claim is grounded in the cited "
        "text, 0.0 if the answer appears post-rationalised (claims not present in the "
        "cited text).\n\n"
        f"ANSWER: {answer['answer']}\n\nCITED SOURCES:\n{cited_text}"
    )
    return _judge(
        [{"role": "system", "content": _RUBRIC_SYSTEM}, {"role": "user", "content": user}],
        model=model,
        temperature=temperature,
        chat=chat,
    ).score
