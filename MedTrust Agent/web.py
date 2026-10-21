"""MedTrust Agent — web dashboard (FastAPI).

A small single-file UI over the ``medtrust`` reference layer so the paper can show
screenshots of: governed query answers with citations, zero-trust denials, step-up
authorization, the tamper-evident audit chain, and live observability counters.

Run (from the Awesome-AI4Med directory):
    /home/sijo/VeritasGraph/.venv/bin/uvicorn medtrust.web:app --port 8400
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from medtrust.agent import MedTrustAgent
from medtrust.iam import User, Action

app = FastAPI(title="MedTrust Agent Dashboard")

# Scenarios exercised by the dashboard (and by the Playwright screenshots).
_SCENARIOS = [
    {
        "id": "clinician-lit",
        "title": "Clinician — literature query",
        "role": "clinician",
        "query": "metformin eGFR limit for diabetes therapy",
        "expect": "approved with citations",
    },
    {
        "id": "guest-denied",
        "title": "Guest — adverse events (least privilege)",
        "role": "guest",
        "query": "adverse event reports for metformin",
        "expect": "denied",
    },
    {
        "id": "analyst-stepup",
        "title": "Safety analyst — export (needs step-up)",
        "role": "safety_analyst",
        "query": "export patient data for cohort P001",
        "expect": "denied until step-up",
    },
]


def _run_all():
    agent = MedTrustAgent()
    rows = []
    for sc in _SCENARIOS:
        user = User(f"u-{sc['role']}", role=sc["role"])
        resp = agent.handle(user, sc["query"])
        rows.append({**sc, "resp": resp})

    # Demonstrate step-up approval for the analyst export.
    analyst = User("u-safety_analyst", role="safety_analyst")
    agent.iam.grant_step_up(analyst, Action.EXPORT_PATIENT_DATA)
    stepup = agent.handle(analyst, "export patient data for cohort P001")
    return agent, rows, stepup


@app.get("/api/run")
def api_run():
    agent, rows, stepup = _run_all()
    return JSONResponse(
        {
            "rows": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "role": r["role"],
                    "query": r["query"],
                    "approved": r["resp"].approved,
                    "reason": r["resp"].reason,
                    "citations": r["resp"].citations,
                    "escalated": r["resp"].escalated,
                    "audit_id": r["resp"].audit_id[:16],
                }
                for r in rows
            ],
            "stepup_approved": stepup.approved,
            "counters": agent.obs.counters,
            "audit_valid": agent.governance.audit.verify(),
        }
    )


def _badge(ok: bool, label_true: str, label_false: str) -> str:
    cls = "ok" if ok else "no"
    txt = label_true if ok else label_false
    return f'<span class="badge {cls}">{txt}</span>'


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    agent, rows, stepup = _run_all()

    cards = []
    for r in rows:
        resp = r["resp"]
        cites = " ".join(f'<code>{c}</code>' for c in resp.citations) or "&mdash;"
        answer = resp.answer or "<em>(no answer returned)</em>"
        cards.append(
            f"""
            <div class="card" data-testid="card-{r['id']}">
              <h3>{r['title']}</h3>
              <div class="meta">role: <b>{r['role']}</b></div>
              <div class="query">Q: {r['query']}</div>
              <div class="status">{_badge(resp.approved, 'APPROVED', 'DENIED')}
                {'<span class="badge warn">ESCALATED</span>' if resp.escalated else ''}</div>
              <div class="reason">{resp.reason}</div>
              <div class="answer">{answer}</div>
              <div class="cites">Citations: {cites}</div>
              <div class="audit">audit: <code>{resp.audit_id[:16] or '—'}</code></div>
            </div>"""
        )

    counters = "".join(
        f'<div class="kpi"><div class="num">{v}</div><div class="lbl">{k}</div></div>'
        for k, v in agent.obs.counters.items()
    )

    stepup_card = f"""
      <div class="card highlight" data-testid="card-stepup">
        <h3>Step-up authorization granted</h3>
        <div class="query">Q: export patient data for cohort P001</div>
        <div class="status">{_badge(stepup.approved, 'APPROVED', 'DENIED')}</div>
        <div class="reason">Same analyst, now with an approved step-up token.</div>
        <div class="audit">audit: <code>{stepup.audit_id[:16]}</code></div>
      </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>MedTrust Agent — Governed Medical LLM Dashboard</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         background:#0b1220; color:#e6edf7; }}
  header {{ padding:28px 40px; background:linear-gradient(120deg,#12203a,#1b3a6b);
            border-bottom:1px solid #223; }}
  header h1 {{ margin:0 0 6px; font-size:26px; }}
  header p {{ margin:0; color:#9fb4d6; }}
  .tag {{ display:inline-block; margin-top:10px; padding:4px 10px; border-radius:20px;
          background:#123; color:#7fe0b0; font-size:12px; border:1px solid #275; }}
  main {{ padding:28px 40px; }}
  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.08em; color:#8aa0c4; }}
  .kpis {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:26px; }}
  .kpi {{ background:#111c31; border:1px solid #223; border-radius:12px; padding:16px 22px; min-width:130px; }}
  .kpi .num {{ font-size:30px; font-weight:700; color:#7fb4ff; }}
  .kpi .lbl {{ font-size:12px; color:#8aa0c4; margin-top:4px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:18px; }}
  .card {{ background:#111c31; border:1px solid #223; border-radius:14px; padding:18px 20px; }}
  .card.highlight {{ border-color:#2b6; box-shadow:0 0 0 1px #2b6 inset; }}
  .card h3 {{ margin:0 0 8px; font-size:16px; }}
  .meta,.query,.reason,.cites,.audit {{ font-size:13px; margin:6px 0; color:#b9c8e2; }}
  .query {{ color:#cddcff; }}
  .answer {{ font-size:13px; margin:8px 0; padding:10px; background:#0d1626; border-radius:8px;
             border:1px solid #1c2c48; color:#dfe9fb; }}
  code {{ background:#0d1626; padding:2px 6px; border-radius:6px; color:#7fe0b0; font-size:12px; }}
  .badge {{ display:inline-block; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; }}
  .badge.ok {{ background:#0f3d2a; color:#5ee6a0; border:1px solid #2b6; }}
  .badge.no {{ background:#3d0f18; color:#ff8095; border:1px solid #a34; }}
  .badge.warn {{ background:#3d310f; color:#ffce6b; border:1px solid #a83; margin-left:6px; }}
  footer {{ padding:20px 40px; color:#6f83a6; font-size:12px; border-top:1px solid #223; }}
</style>
</head>
<body>
  <header>
    <h1>MedTrust Agent — Governed Medical LLM Dashboard</h1>
    <p>Zero-trust · grounded citations · tamper-evident audit · SRE observability</p>
    <span class="tag" data-testid="audit-valid">Audit chain valid: {str(agent.governance.audit.verify())}</span>
  </header>
  <main>
    <h2>Observability counters</h2>
    <div class="kpis" data-testid="kpis">{counters}</div>

    <h2>Governed request scenarios</h2>
    <div class="grid">{''.join(cards)}{stepup_card}</div>
  </main>
  <footer>
    MedTrust Agent reference layer · maps to VeritasGraph (studio_api, veritasgraph_mcp,
    veritas-reason, clinical-kg, future-agi). Deterministic, on-prem, no external egress.
  </footer>
</body>
</html>"""
