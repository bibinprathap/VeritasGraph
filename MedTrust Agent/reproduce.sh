#!/usr/bin/env bash
# Reproduce all MedTrust Agent results (reviewer R2-5: publish code, seeds, scenarios).
#
# Usage:
#   ./medtrust/reproduce.sh            # full offline reproduction
#   SEED=7 TRIALS=30 ./medtrust/reproduce.sh
#
# Produces (under medtrust/results/ and medtrust/diagrams/):
#   metrics.json   - ablation (measured security + illustrative quality), 95% CI
#   latency.json   - absolute per-component latency (microseconds)
#   security.json  - injection benchmark, adaptive attack, false-denial, conformance
#   diagram*.pdf/png - the five figures (editorial "technical blueprint" theme)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

PY="${PY:-/home/sijo/VeritasGraph/.venv/bin/python}"
SEED="${SEED:-7}"
TRIALS="${TRIALS:-30}"

echo "== MedTrust Agent reproduction =="
echo "python : $PY"
echo "seed   : $SEED   trials: $TRIALS"
echo

echo "[1/4] Unit + integrity + security tests"
"$PY" -m pytest medtrust/tests -q

echo "[2/4] Ablation + per-component latency (seed=$SEED, trials=$TRIALS)"
"$PY" -m medtrust.benchmark --trials "$TRIALS" --seed "$SEED"

echo "[3/4] Adversarial security evaluation"
"$PY" -m medtrust.eval.attacks

echo "[4/4] Figures"
"$PY" medtrust/diagrams.py

echo "[5/5] Submission gate (figures synced, EDAS compliance, citations, acronyms)"
cp medtrust/diagrams/diagram*.pdf paper_ieee/graphics/ 2>/dev/null || true
"$PY" scripts/check_submission.py || echo "  (gate warnings above; rebuild paper if figures changed)"

echo
echo "Done. Artifacts:"
echo "  medtrust/results/metrics.json"
echo "  medtrust/results/latency.json"
echo "  medtrust/results/security.json"
echo "  medtrust/diagrams/*.pdf"
echo
echo "Optional live-LLM track (real model + public data):"
echo "  set MEDTRUST_LLM_URL / MEDTRUST_LLM_MODEL and use medtrust/llm.py"
