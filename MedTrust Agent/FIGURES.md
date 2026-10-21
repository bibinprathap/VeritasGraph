# MedTrust Agent — Figures (Playwright-captured)

These screenshots were captured automatically by `medtrust/screenshots.py` driving the
live dashboard (`medtrust/web.py`) with Playwright/Chromium. The same script also
asserts the governed behaviors (5/5 checks passed), so the figures are verified, not
hand-made.

Reproduce:

```bash
# 1. start the dashboard
cd Awesome-AI4Med
/home/sijo/VeritasGraph/.venv/bin/uvicorn medtrust.web:app --port 8400 &

# 2. run the Playwright test + capture
/home/sijo/VeritasGraph/.venv/bin/python medtrust/screenshots.py
```

| Figure | File | Shows | Paper section |
|--------|------|-------|---------------|
| Fig 1 | `screenshots/fig1_dashboard_full.png` | Full governed dashboard (all scenarios + KPIs) | §3 Proposed System |
| Fig 2 | `screenshots/fig2_observability_kpis.png` | Observability counters (requests/answered/blocked/step-up) | §3.5 Observability |
| Fig 3 | `screenshots/fig3_approved_with_citations.png` | Approved clinician answer with `[doc#chunk]` citations | §3.2 / §3.4 |
| Fig 4 | `screenshots/fig4_zero_trust_denied.png` | Least-privilege denial (guest → adverse events) | §3.3 Zero-Trust |
| Fig 5 | `screenshots/fig5_stepup_required.png` | High-risk export blocked, escalated for step-up | §3.3 Zero-Trust |
| Fig 6 | `screenshots/fig6_stepup_approved.png` | Same export approved after step-up authorization | §3.3 Zero-Trust |

**Verified behaviors (Playwright assertions):**
- audit chain reports valid,
- clinician literature query is APPROVED and shows a `pubmed_001` citation,
- guest adverse-event query is DENIED,
- analyst export is ESCALATED (step-up required),
- analyst export becomes APPROVED after step-up.
