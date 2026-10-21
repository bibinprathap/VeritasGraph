# MedTrust Agent — Paper Diagrams (rendered)

Five publication-quality figures, rendered **offline** by `medtrust/diagrams.py`
(pure matplotlib — no internet, Node, or mermaid-cli required).

Reproduce:

```bash
cd Awesome-AI4Med
/home/sijo/VeritasGraph/.venv/bin/python medtrust/diagrams.py
```

| Figure | File | Type | Shows | Paper section |
|--------|------|------|-------|---------------|
| 1 | `diagrams/diagram1_system_architecture.png` | Architecture | 5-layer system inside the zero-trust boundary | §3 Proposed System |
| 2 | `diagrams/diagram2_request_sequence.png` | Sequence | Authorize → step-up → retrieve → govern → observe → answer | §3.1 / §3.3 |
| 3 | `diagrams/diagram3_module_mapping.png` | Mapping | `medtrust/` modules ↔ VeritasGraph engines (reuse + reproducibility) | §3 / §6 |
| 4 | `diagrams/diagram4_threat_model.png` | Security | Each attack → the control that blocks it | §3.3 / §5 Security |
| 5 | `diagrams/diagram5_results_ablation.png` | Results | Ablation across 5 build variants (accuracy, hallucination, policy, access) | §5 Results |

**Notes**
- Figures 1–4 are structural and final.
- Figure 5 uses illustrative target values from `results_build_plan.md`; replace the
  arrays in `diagrams.py::diagram5()` with measured numbers after evaluation runs.
- Also available: live-dashboard screenshots in `medtrust/FIGURES.md` (captured via
  Playwright) as an appendix "it runs" proof.
