# MedTrust Agent — Reproducibility Artifact

This artifact accompanies *MedTrust Agent: A Zero-Trust, Observable LLM Agent
Framework for Medical and Pharmaceutical Workflows* (NEECON 2026). It lets a
reviewer reproduce **every number and figure** in the paper from source, with
fixed seeds and versioned scenarios (reviewer R2-5).

## 1. What is measured vs. illustrative (reviewer R2-1)

| Result | Status | Source |
|---|---|---|
| Unauthorized-access blocked | **Measured** | Real IAM gate (`iam.py`) over 40 independent scenarios; Wilson 95% CI |
| Citations enforced | **Measured** | Real governance engine (`governance.py`) |
| Audit tamper-evidence (mutation/truncation/recompute/rollback) | **Measured** | `tests/test_audit.py` |
| Prompt-injection block rate, adaptive bypass, false-denial, IAM conformance | **Measured** | `eval/attacks.py`; Wilson 95% CI |
| Per-component latency (IAM/retrieval/governance/observability) | **Measured** | `benchmark.py` wall-clock, `results/latency.json` |
| Answer accuracy / hallucination | **Illustrative (seeded model)** | `benchmark._quality_model`; reproduce with a real model via `llm.py` |

Headline claims rest on the **measured** metrics. The answer-quality track is
clearly labelled *illustrative* everywhere; a live-LLM path is provided so the
quality track can be re-run on public data.

## 2. Environment

```bash
# Python 3.11+ ; project venv already contains the deps:
PY=/home/sijo/VeritasGraph/.venv/bin/python
$PY -m pip install -r medtrust/requirements.txt   # if recreating the env
```

Core deps: `matplotlib`, `numpy`, `pytest` (offline). Optional for the live
track: an OpenAI-compatible endpoint (vLLM / Ollama / llama.cpp / OpenAI).

## 3. One-command reproduction

```bash
./medtrust/reproduce.sh                 # tests + metrics + latency + security + figures
SEED=7 TRIALS=30 ./medtrust/reproduce.sh
```

Individual steps:

```bash
$PY -m pytest medtrust/tests -q                         # 34 tests
$PY -m medtrust.benchmark --trials 30 --seed 7          # metrics.json + latency.json
$PY -m medtrust.eval.attacks                            # security.json
$PY medtrust/diagrams.py                                # 5 figures (PDF+PNG)
```

## 4. Fixed inputs (versioned)

- **Seeds:** default `--seed 7`, `--trials 30` (30 independent trials × 40 scenarios).
- **Scenarios:** `medtrust/scenarios/scenarios.jsonl` (40 cases across 6
  categories: clinical QA, pharmacovigilance, trial access, PHI handling,
  prompt injection, privilege escalation).
- **Injection corpus:** `eval/attacks.py::PI_CORPUS` (direct / indirect /
  exfiltration / jailbreak families + benign controls).
- **Audit key:** `MEDTRUST_AUDIT_KEY` (defaults to a dev key; set a real secret
  in production — key secrecy is the stated tamper-evidence assumption).

## 5. Expected outputs (seed 7, 30 trials)

- `results/metrics.json`: MT blocks **100%** unauthorized (Wilson CI over
  independent cases), **100%** citations enforced; accuracy/hallucination
  labelled illustrative.
- `results/latency.json`: IAM ≈ 0.8 µs, governance+audit ≈ 2.5 µs per request;
  full stack ≈ 7–8 µs total vs ≈ 5.5 µs for the tool-agent baseline
  (**MT/B3 ≈ 1.4×** on a microsecond base — negligible against real LLM
  inference of 100s of ms).
- `results/security.json`: one-shot injection block **100%**; adaptive
  obfuscation reveals substring-filter evasion (motivating defence-in-depth);
  false-denial **0%**; IAM spec conformance **100%** over the full
  role × action × step-up space.

## 6. Live-LLM track (real model + public data)

```bash
export MEDTRUST_LLM_URL=http://localhost:11434/v1   # e.g. Ollama
export MEDTRUST_LLM_MODEL=llama3
$PY - <<'PY'
from medtrust.llm import OpenAICompatibleClient, load_public_cases, evaluate_live
cases = load_public_cases("path/to/public_qa.jsonl")   # {qid,question,gold,options?}
print(evaluate_live(OpenAICompatibleClient(), cases))
PY
```

The grounding, citation enforcement, IAM, and audit layers remain the real
control-plane modules; only the generator is swapped for the live model.

## 7. File map

```
medtrust/
  iam.py              zero-trust / least-privilege + step-up
  retrieval.py        grounding + [doc#chunk] citations
  governance.py       policy + keyed, anchored, tamper-evident audit
  observability.py    spans + counters
  agent.py            orchestration
  benchmark.py        ablation + per-component latency  -> results/*.json
  eval/attacks.py     injection benchmark + adaptive attack + conformance + FNR
  eval/stats.py       Wilson / bootstrap intervals
  llm.py              optional live-LLM adapter (public data)
  diagrams.py         5 figures (editorial theme)
  scenarios/scenarios.jsonl   versioned scenario suite
  reproduce.sh        one-command reproduction
  tests/              34 tests (unit + audit + security)
```
