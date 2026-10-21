"""TC-24/TC-25 — Live-LLM adapter coverage (reviewer R2-1).

The real-model path (``medtrust/llm.py``) is exercised with an in-process stub
client so no network or live endpoint is required. We verify prompt grounding,
governance enforcement on the live path, scoring, and the public-case loader.
"""

from __future__ import annotations

import json

from medtrust.llm import (
    LLMClient, PublicCase, load_public_cases, evaluate_live, _score,
)


class StubClient:
    """Returns a fixed answer regardless of prompt (no network)."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


def test_score_containment_matcher():
    assert _score("Metformin is first-line therapy", "metformin") is True
    assert _score("unrelated text", "warfarin") is False


def test_load_public_cases(tmp_path):
    p = tmp_path / "qa.jsonl"
    p.write_text(
        json.dumps({"qid": "q1", "question": "Q?", "gold": "metformin"}) + "\n"
        + json.dumps({"qid": "q2", "question": "Q2?", "gold": "insulin",
                      "options": ["a", "b"]}) + "\n"
    )
    cases = load_public_cases(str(p))
    assert len(cases) == 2
    assert cases[0].qid == "q1"
    assert cases[1].options == ["a", "b"]


def test_evaluate_live_grounds_and_scores_correct_answer():
    client = StubClient("Metformin is first-line therapy for diabetes.")
    cases = [PublicCase("q1", "First-line for T2DM?", "metformin")]
    out = evaluate_live(client, cases)
    assert out["n"] == 1
    assert out["answered"] == 1
    assert out["correct"] == 1
    assert out["accuracy"]["mean"] == 1.0
    # the prompt must include retrieved evidence (grounding) before the question
    assert "Evidence:" in client.prompts[0]


def test_evaluate_live_counts_wrong_answer_as_incorrect():
    client = StubClient("The capital of France is Paris.")
    cases = [PublicCase("q1", "First-line for T2DM?", "metformin")]
    out = evaluate_live(client, cases)
    assert out["answered"] == 1
    assert out["correct"] == 0
    assert out["accuracy"]["mean"] == 0.0


def test_evaluate_live_makes_no_network_call():
    """StubClient has no network; evaluate_live must rely only on it."""
    client = StubClient("Metformin is first-line therapy.")
    cases = [PublicCase(f"q{i}", "First-line for T2DM?", "metformin") for i in range(3)]
    out = evaluate_live(client, cases)
    assert out["n"] == 3
    assert len(client.prompts) == 3
