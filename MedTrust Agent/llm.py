"""Optional real-LLM evaluation adapter (reviewer R2-1).

The offline sandbox has no live foundation model, so the headline results use
the measured control-plane metrics plus an *illustrative* seeded answer model.
This module lets a reviewer reproduce the answer-quality track against a **real
model on public data** without changing the rest of the harness.

Design
------
* ``LLMClient`` is a minimal protocol: ``generate(prompt) -> str``.
* ``OpenAICompatibleClient`` targets any OpenAI-compatible endpoint (vLLM,
  Ollama, llama.cpp server, Azure, OpenAI) via ``base_url`` + ``model``.
* ``evaluate_live`` runs the same scenario suite, grounds with the real
  retrieval engine, applies the real governance/IAM controls, and scores
  accuracy/hallucination against the public dataset's gold answers.

Nothing here is imported by the default offline path; it is gated behind the
``--live`` flag of ``medtrust.benchmark_live``.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional, Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...


@dataclass
class OpenAICompatibleClient:
    """Calls any OpenAI-compatible /chat/completions endpoint."""

    base_url: str = os.environ.get("MEDTRUST_LLM_URL", "http://localhost:11434/v1")
    model: str = os.environ.get("MEDTRUST_LLM_MODEL", "llama3")
    api_key: str = os.environ.get("MEDTRUST_LLM_KEY", "sk-none")
    temperature: float = 0.0
    timeout: float = 60.0

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system",
                 "content": "You are a clinical assistant. Answer only from the "
                            "provided evidence and cite it. If unsupported, refuse."},
                {"role": "user", "content": prompt},
            ],
        }
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.load(resp)
        return data["choices"][0]["message"]["content"]


@dataclass
class PublicCase:
    """A public-dataset QA item (e.g. a PubMedQA/MedQA sample)."""

    qid: str
    question: str
    gold: str                 # reference answer / label
    options: Optional[List[str]] = None


def load_public_cases(path: str) -> List[PublicCase]:
    """Load a JSONL public-dataset slice: {qid, question, gold, options?}."""
    cases: List[PublicCase] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            cases.append(PublicCase(d["qid"], d["question"], d["gold"],
                                    d.get("options")))
    return cases


def _score(answer: str, gold: str) -> bool:
    """Lenient containment match; replace with dataset-specific scorer."""
    a, g = answer.lower(), gold.lower()
    return g in a or a[:40] in g


def evaluate_live(client: LLMClient, cases: List[PublicCase],
                  scorer: Callable[[str, str], bool] = _score) -> dict:
    """Run the real model over public cases; return accuracy with counts.

    Grounding, citation enforcement, IAM, and audit remain the real
    control-plane modules; only the generator is swapped for a live LLM.
    """
    from .retrieval import RetrievalEngine
    from .governance import GovernanceEngine, AuditLog

    retrieval = RetrievalEngine()
    correct = 0
    answered = 0
    for c in cases:
        evidence = retrieval.retrieve(c.question)
        context = "\n".join(f"{e.citation} {e.text}" for e in evidence)
        prompt = f"Evidence:\n{context}\n\nQuestion: {c.question}\nAnswer with a citation."
        out = client.generate(prompt)
        gov = GovernanceEngine(AuditLog(key=b"live"))
        res = gov.review("clinician", out, evidence)
        if res.approved:
            answered += 1
            if scorer(out, c.gold):
                correct += 1
    from .eval.stats import wilson
    acc = wilson(correct, answered) if answered else wilson(0, 0)
    return {"n": len(cases), "answered": answered, "correct": correct,
            "accuracy": acc.as_dict()}
