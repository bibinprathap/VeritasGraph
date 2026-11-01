"""MedTrust Agent — Clinical Information System (CIS) themed dashboard.

An alternate front-end over the same ``medtrust`` reference layer, styled to look
like enterprise, on-prem healthcare software (Epic/Cerner-era CIS): a light,
paper-toned workspace with a left module rail, a utility bar, dense data tables,
serif section headers, and a desktop-style status footer. Deliberately *not* the
dark, gradient "AI demo" aesthetic.

Run (from the Awesome-AI4Med directory):
    /home/sijo/VeritasGraph/.venv/bin/uvicorn medtrust.web_clinical:app --port 8410
"""

from __future__ import annotations

import datetime as _dt

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from medtrust.agent import MedTrustAgent
from medtrust.iam import Action, HIGH_RISK, User, _ROLE_PERMISSIONS
from medtrust.retrieval import RetrievalEngine

app = FastAPI(title="MedTrust CIS")

_SCENARIOS = [
  {
    "id": "clinician-lit",
    "title": "Literature lookup",
    "role": "clinician",
    "query": "metformin eGFR limit for diabetes therapy",
  },
  {
    "id": "guest-denied",
    "title": "Adverse-event pull",
    "role": "guest",
    "query": "adverse event reports for metformin",
  },
  {
    "id": "analyst-stepup",
    "title": "Patient-data export",
    "role": "safety_analyst",
    "query": "export patient data for cohort P001",
  },
]

_ORDERED_COUNTERS = [
  "requests",
  "answered",
  "access_blocked",
  "step_up_required",
  "governance_blocked",
  "unsupported",
]

_ROUTE_TO_TAB = {
  "dashboard": "Dashboard",
  "access-governance": "Access & Governance",
  "retrieval-sources": "Retrieval Sources",
  "audit-ledger": "Audit Ledger",
  "adverse-events": "Adverse Events",
  "pharmacovigilance": "Pharmacovigilance",
  "policy-rules": "Policy Rules",
  "observability": "Observability",
  "identity-iam": "Identity (IAM)",
}


def _run_all():
  agent = MedTrustAgent()
  rows = []
  for sc in _SCENARIOS:
    user = User(f"u-{sc['role']}", role=sc["role"])
    resp = agent.handle(user, sc["query"])
    rows.append({**sc, "resp": resp})
  analyst = User("u-safety_analyst", role="safety_analyst")
  agent.iam.grant_step_up(analyst, Action.EXPORT_PATIENT_DATA)
  stepup = agent.handle(analyst, "export patient data for cohort P001")
  return agent, rows, stepup


def _pill(state: str) -> str:
  state = state.upper()
  cls = {
    "APPROVED": "ok",
    "DENIED": "no",
    "STEP-UP": "warn",
    "AUTHORIZED": "ok",
    "BLOCKED": "no",
    "VERIFIED": "ok",
    "TAMPERED": "no",
  }.get(state, "muted")
  return f'<span class="pill {cls}">{state}</span>'


def _kpi_tiles(counters: dict[str, int]) -> str:
  parts = []
  for key in _ORDERED_COUNTERS:
    if key in counters:
      parts.append(
        f'<div class="metric"><span class="mv">{counters[key]}</span>'
        f'<span class="mk">{key.replace("_", " ")}</span></div>'
      )
  return "".join(parts)


def _register_rows(rows, stepup) -> str:
  body_rows = []
  for i, row in enumerate(rows, 1):
    resp = row["resp"]
    state = "APPROVED" if resp.approved else ("STEP-UP" if resp.escalated else "DENIED")
    cites = ", ".join(resp.citations) if resp.citations else "—"
    audit = resp.audit_id[:12] if resp.audit_id else "—"
    body_rows.append(
      f"""<tr>
        <td class="idx">{i:02d}</td>
        <td>{row['title']}</td>
        <td class="mono">{row['role']}</td>
        <td class="q">{row['query']}</td>
        <td class="ctr">{_pill(state)}</td>
        <td class="mono cites">{cites}</td>
        <td class="mono">{audit}</td>
      </tr>"""
    )

  stepup_state = "AUTHORIZED" if stepup.approved else "BLOCKED"
  body_rows.append(
    f"""<tr class="follow">
      <td class="idx">03a</td>
      <td>Patient-data export <span class="note">(re-submitted with approval)</span></td>
      <td class="mono">safety_analyst</td>
      <td class="q">export patient data for cohort P001</td>
      <td class="ctr">{_pill(stepup_state)}</td>
      <td class="mono cites">step-up token</td>
      <td class="mono">{stepup.audit_id[:12]}</td>
    </tr>"""
  )
  return "".join(body_rows)


def _nav(active: str, counts: dict[str, int]) -> str:
  def item(path: str, label: str, key: str, count: int | None = None) -> str:
    active_cls = " class=\"active\"" if active == key else ""
    count_html = f'<span class="c">{count}</span>' if count is not None else ""
    return f'<a href="/{path}"{active_cls}><span>{label}</span>{count_html}</a>'

  return (
    '<div class="grp">Workspace</div>'
    + item("dashboard", "Dashboard", "dashboard")
    + item("access-governance", "Access &amp; Governance", "access-governance", counts["access"])
    + item("retrieval-sources", "Retrieval Sources", "retrieval-sources", counts["retrieval"])
    + item("audit-ledger", "Audit Ledger", "audit-ledger", counts["audit"])
    + '<div class="grp">Safety</div>'
    + item("adverse-events", "Adverse Events", "adverse-events")
    + item("pharmacovigilance", "Pharmacovigilance", "pharmacovigilance")
    + item("policy-rules", "Policy Rules", "policy-rules")
    + '<div class="grp">System</div>'
    + item("observability", "Observability", "observability")
    + item("identity-iam", "Identity (IAM)", "identity-iam")
  )


def _access_page(agent, rows, stepup) -> str:
  audit_ok = agent.governance.audit.verify()
  audit_state = "VERIFIED" if audit_ok else "TAMPERED"
  return f"""
    <div class="sec">Session metrics</div>
    <div class="metrics" data-testid="kpis">{_kpi_tiles(agent.obs.counters)}</div>

    <div class="sec">Request register</div>
    <table data-testid="register">
    <thead>
      <tr><th>#</th><th>Task</th><th>Role</th><th>Query</th><th>Decision</th>
        <th>Citations</th><th>Audit ref</th></tr>
    </thead>
    <tbody>
      {_register_rows(rows, stepup)}
    </tbody>
    </table>

    <div class="callout" data-testid="audit-valid">
    <span class="k">Audit ledger integrity</span>
    <span class="badge {'ok' if audit_ok else 'no'}">{audit_state}</span>
    <span class="k">entries</span>
    <span class="hash">{len(agent.governance.audit)}</span>
    <span class="k">chain</span>
    <span class="hash">SHA-256 · hash-linked</span>
    </div>
  """


def _dashboard_page(agent, rows, stepup) -> str:
  approvals = sum(1 for row in rows if row["resp"].approved) + (1 if stepup.approved else 0)
  blocked = sum(1 for row in rows if not row["resp"].approved)
  return f"""
    <div class="sec">At-a-glance</div>
    <div class="metrics">
    <div class="metric"><span class="mv">{approvals}</span><span class="mk">approved decisions</span></div>
    <div class="metric"><span class="mv">{blocked}</span><span class="mk">blocked decisions</span></div>
    <div class="metric"><span class="mv">{len(agent.governance.audit)}</span><span class="mk">audit entries</span></div>
    </div>

    <div class="sec">Workflow checkpoints</div>
    <table>
    <thead><tr><th>Control</th><th>Status</th><th>Notes</th></tr></thead>
    <tbody>
      <tr><td>Least privilege gate</td><td>{_pill('APPROVED')}</td><td>Access checks run before tools execute.</td></tr>
      <tr><td>Citation-grounded output</td><td>{_pill('APPROVED')}</td><td>Released answers include document/chunk citations.</td></tr>
      <tr><td>Step-up on high-risk actions</td><td>{_pill('STEP-UP')}</td><td>Export actions require elevated approval.</td></tr>
      <tr><td>Audit chain integrity</td><td>{_pill('VERIFIED' if agent.governance.audit.verify() else 'TAMPERED')}</td><td>Keyed chain validates for this session.</td></tr>
    </tbody>
    </table>
  """


def _retrieval_sources_page() -> str:
  rows = []
  for ev in RetrievalEngine()._corpus:  # deterministic in-memory reference corpus
    rows.append(
      f"<tr><td class=\"mono\">{ev.citation}</td><td class=\"mono\">{ev.doc_id}</td><td>{ev.text}</td></tr>"
    )
  return f"""
    <div class="sec">Grounding corpus</div>
    <table>
    <thead><tr><th>Citation</th><th>Document</th><th>Evidence text</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
    </table>
  """


def _audit_ledger_page(agent) -> str:
  rows = []
  for entry in agent.governance.audit._entries:
    ts = _dt.datetime.fromtimestamp(entry.ts).strftime("%Y-%m-%d %H:%M:%S")
    rows.append(
      f"""<tr>
        <td class="mono">{entry.index}</td>
        <td class="mono">{entry.actor}</td>
        <td class="mono">{entry.action}</td>
        <td>{entry.decision}</td>
        <td class="mono">{ts}</td>
        <td class="mono">{entry.prev_hash[:16]}</td>
        <td class="mono">{entry.entry_hash[:16]}</td>
      </tr>"""
    )
  return f"""
    <div class="sec">Ledger entries</div>
    <table>
    <thead><tr><th>#</th><th>Actor</th><th>Action</th><th>Decision</th><th>Timestamp</th><th>Prev hash</th><th>Entry hash</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
    </table>
    <div class="callout">
    <span class="k">Chain verification</span>
    <span class="badge {'ok' if agent.governance.audit.verify() else 'no'}">{'VERIFIED' if agent.governance.audit.verify() else 'TAMPERED'}</span>
    </div>
  """


def _adverse_events_page(rows) -> str:
  event_row = next(row for row in rows if row["id"] == "guest-denied")
  resp = event_row["resp"]
  return f"""
    <div class="sec">Adverse-event access attempt</div>
    <table>
    <thead><tr><th>Role</th><th>Query</th><th>Decision</th><th>Reason</th></tr></thead>
    <tbody>
      <tr>
      <td class="mono">{event_row['role']}</td>
      <td>{event_row['query']}</td>
      <td>{_pill('DENIED')}</td>
      <td>{resp.reason}</td>
      </tr>
    </tbody>
    </table>
  """


def _pharmacovigilance_page(rows, stepup) -> str:
  scenario = next(row for row in rows if row["id"] == "analyst-stepup")
  return f"""
    <div class="sec">Safety analyst flow</div>
    <table>
    <thead><tr><th>Stage</th><th>Decision</th><th>Reason</th></tr></thead>
    <tbody>
      <tr><td>Initial export request</td><td>{_pill('STEP-UP')}</td><td>{scenario['resp'].reason}</td></tr>
      <tr><td>Post-approval resubmission</td><td>{_pill('AUTHORIZED' if stepup.approved else 'BLOCKED')}</td><td>{stepup.reason}</td></tr>
    </tbody>
    </table>
  """


def _policy_rules_page() -> str:
  rows = []
  for role, actions in sorted(_ROLE_PERMISSIONS.items()):
    action_labels = ", ".join(sorted(action.value for action in actions))
    rows.append(f"<tr><td class=\"mono\">{role}</td><td>{action_labels}</td></tr>")
  high_risk = ", ".join(sorted(action.value for action in HIGH_RISK))
  return f"""
    <div class="sec">Role permission matrix</div>
    <table>
    <thead><tr><th>Role</th><th>Allowed actions</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
    </table>
    <div class="callout"><span class="k">High-risk actions requiring step-up</span><span class="hash">{high_risk}</span></div>
  """


def _observability_page(agent) -> str:
  counter_rows = [
    f"<tr><td>{name}</td><td class=\"mono\">{value}</td></tr>"
    for name, value in sorted(agent.obs.counters.items())
  ]
  span_rows = []
  for span in agent.obs.spans:
    span_rows.append(
      f"<tr><td class=\"mono\">{span.name}</td><td class=\"mono\">{span.duration_ms:.3f}</td><td class=\"mono\">{span.attributes}</td></tr>"
    )
  return f"""
    <div class="sec">Counters</div>
    <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>{''.join(counter_rows)}</tbody>
    </table>

    <div class="sec">Trace spans</div>
    <table>
    <thead><tr><th>Span</th><th>Duration (ms)</th><th>Attributes</th></tr></thead>
    <tbody>{''.join(span_rows)}</tbody>
    </table>
  """


def _identity_page(rows) -> str:
  checks = []
  for row in rows:
    resp = row["resp"]
    decision = "APPROVED" if resp.approved else ("STEP-UP" if resp.escalated else "DENIED")
    checks.append(
      f"<tr><td class=\"mono\">{row['role']}</td><td>{row['title']}</td><td>{_pill(decision)}</td><td>{resp.reason}</td></tr>"
    )
  return f"""
    <div class="sec">Role-based authorization checks</div>
    <table>
    <thead><tr><th>Role</th><th>Operation</th><th>Decision</th><th>Reason</th></tr></thead>
    <tbody>{''.join(checks)}</tbody>
    </table>
  """


def _page_content(active: str, agent, rows, stepup) -> tuple[str, str, str]:
  if active == "dashboard":
    return (
      "Clinical Dashboard",
      "Operational summary of governance controls, approvals, and ledger status.",
      _dashboard_page(agent, rows, stepup),
    )
  if active == "access-governance":
    return (
      "Access & Governance Review",
      "Each request is authorized before execution, grounded with citations, and recorded in the audit ledger.",
      _access_page(agent, rows, stepup),
    )
  if active == "retrieval-sources":
    return (
      "Retrieval Sources",
      "Deterministic source corpus used to ground every released response.",
      _retrieval_sources_page(),
    )
  if active == "audit-ledger":
    return (
      "Audit Ledger",
      "Keyed, hash-linked entries with chain verification for tamper-evidence.",
      _audit_ledger_page(agent),
    )
  if active == "adverse-events":
    return (
      "Adverse Events",
      "Review adverse-event query handling under least-privilege constraints.",
      _adverse_events_page(rows),
    )
  if active == "pharmacovigilance":
    return (
      "Pharmacovigilance",
      "Step-up authorization flow for high-risk safety analyst operations.",
      _pharmacovigilance_page(rows, stepup),
    )
  if active == "policy-rules":
    return (
      "Policy Rules",
      "Role permission matrix and step-up requirements for sensitive actions.",
      _policy_rules_page(),
    )
  if active == "observability":
    return (
      "Observability",
      "Counters and spans emitted by the control plane for each governed request.",
      _observability_page(agent),
    )
  return (
    "Identity (IAM)",
    "Role-scoped authorization outcomes for representative MedTrust scenarios.",
    _identity_page(rows),
  )


def _render(active: str) -> str:
  agent, rows, stepup = _run_all()
  now = _dt.datetime(2026, 9, 13, 14, 22).strftime("%Y-%m-%d %H:%M")
  title, lead, content = _page_content(active, agent, rows, stepup)
  counts = {
    "access": len(rows) + 1,
    "retrieval": len(RetrievalEngine()._corpus),  # deterministic reference corpus
    "audit": len(agent.governance.audit),
  }

  return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>MedTrust CIS — {title}</title>
<style>
  :root {{
    --paper:#f3f1ea; --panel:#fbfaf6; --ink:#20241f; --sub:#5c6157;
    --line:#d8d3c6; --line2:#e7e2d6;
    --teal:#0f6b5f; --teal-bg:#e2efe9;
    --ox:#8a2d2d; --ox-bg:#f2e2df;
    --amber:#8a5a00; --amber-bg:#f3e9d4;
    --rail:#25332f;
  }}
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; }}
  body {{
    font-family:"Segoe UI", "Helvetica Neue", Arial, sans-serif;
    background:var(--paper); color:var(--ink); font-size:14px; line-height:1.45;
  }}
  .app {{ display:grid; grid-template-columns:232px 1fr; min-height:100vh; }}

  /* Left module rail — like a clinical desktop app */
  .rail {{ background:var(--rail); color:#cdd8d2; padding:0; border-right:3px solid #16211d; }}
  .brand {{ padding:18px 18px 14px; border-bottom:1px solid #33443e; }}
  .brand .logo {{ display:flex; align-items:center; gap:9px; }}
  .brand .mark {{ width:26px; height:26px; border:2px solid #6fb8a6; border-radius:4px;
                  display:grid; place-items:center; color:#8fd4c2; font-weight:800;
                  font-family:Georgia, serif; }}
  .brand .name {{ font-family:Georgia,'Times New Roman',serif; font-size:16px; color:#f0efe8;
                  letter-spacing:.2px; }}
  .brand .sys {{ font-size:11px; color:#8ea79e; margin-top:2px; letter-spacing:.14em;
                 text-transform:uppercase; }}
  .rail nav {{ padding:10px 0; }}
  .rail .grp {{ font-size:10.5px; text-transform:uppercase; letter-spacing:.16em;
                color:#7f978e; padding:12px 18px 6px; }}
  .rail a {{ display:flex; justify-content:space-between; padding:8px 18px; color:#c4d2cb;
             text-decoration:none; border-left:3px solid transparent; font-size:13px; }}
  .rail a .c {{ color:#7f978e; font-variant-numeric:tabular-nums; }}
  .rail a.active {{ background:#2f403a; color:#fff; border-left-color:#6fb8a6; }}
  .rail a:hover {{ background:#2b3a35; }}

  /* Utility bar */
  .top {{ display:flex; align-items:center; justify-content:space-between;
          padding:10px 22px; background:var(--panel); border-bottom:1px solid var(--line); }}
  .crumb {{ font-size:12.5px; color:var(--sub); }}
  .crumb b {{ color:var(--ink); }}
  .top .right {{ display:flex; align-items:center; gap:14px; }}
  .env {{ font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--teal);
          border:1px solid #bcd8cd; background:var(--teal-bg); padding:3px 9px; border-radius:3px; }}
  .user {{ display:flex; align-items:center; gap:8px; font-size:13px; }}
  .user .av {{ width:26px; height:26px; border-radius:50%; background:#c9bfa6; color:#4a4636;
               display:grid; place-items:center; font-weight:700; font-size:12px; }}

  main {{ padding:22px 26px 60px; }}
  .pagehead {{ display:flex; align-items:flex-end; justify-content:space-between;
               border-bottom:2px solid var(--ink); padding-bottom:10px; margin-bottom:4px; }}
  .pagehead h1 {{ font-family:Georgia,'Times New Roman',serif; font-weight:600;
                  font-size:22px; margin:0; letter-spacing:.2px; }}
  .pagehead .stamp {{ font-size:12px; color:var(--sub); font-variant-numeric:tabular-nums; }}
  .lead {{ color:var(--sub); font-size:13px; margin:8px 0 20px; max-width:70ch; }}

  .sec {{ font-family:Georgia,serif; font-size:13px; letter-spacing:.02em; color:var(--ink);
          text-transform:uppercase; border-left:3px solid var(--teal); padding-left:9px;
          margin:22px 0 12px; }}

  /* Metric bar */
  .metrics {{ display:flex; gap:0; border:1px solid var(--line); background:var(--panel);
              border-radius:4px; overflow:hidden; }}
  .metric {{ flex:1; padding:12px 16px; border-right:1px solid var(--line2); }}
  .metric:last-child {{ border-right:0; }}
  .metric .mv {{ display:block; font-size:24px; font-weight:700; font-family:Georgia,serif;
                 color:var(--ink); font-variant-numeric:tabular-nums; }}
  .metric .mk {{ display:block; font-size:11px; color:var(--sub); text-transform:uppercase;
                 letter-spacing:.08em; margin-top:2px; }}

  /* Data table */
  table {{ width:100%; border-collapse:collapse; background:var(--panel);
           border:1px solid var(--line); border-radius:4px; overflow:hidden; }}
  thead th {{ text-align:left; font-size:11px; letter-spacing:.09em; text-transform:uppercase;
              color:var(--sub); background:#eeeade; padding:9px 12px;
              border-bottom:1px solid var(--line); }}
  tbody td {{ padding:11px 12px; border-bottom:1px solid var(--line2); vertical-align:top; }}
  tbody tr:last-child td {{ border-bottom:0; }}
  tbody tr.follow td {{ background:#f6f4ec; }}
  .idx {{ color:var(--sub); font-variant-numeric:tabular-nums; width:44px; }}
  .mono {{ font-family:"Cascadia Mono", Consolas, "Courier New", monospace; font-size:12.5px; }}
  .q {{ color:#3c4238; max-width:280px; }}
  .cites {{ color:var(--teal); }}
  .ctr {{ white-space:nowrap; }}
  .note {{ color:var(--sub); font-size:12px; }}

  .pill {{ display:inline-block; font-size:11px; font-weight:700; letter-spacing:.05em;
           padding:3px 9px; border-radius:3px; text-transform:uppercase;
           border:1px solid transparent; }}
  .pill.ok {{ color:var(--teal); background:var(--teal-bg); border-color:#bcd8cd; }}
  .pill.no {{ color:var(--ox); background:var(--ox-bg); border-color:#dcc2be; }}
  .pill.warn {{ color:var(--amber); background:var(--amber-bg); border-color:#dfcfa6; }}
  .pill.muted {{ color:var(--sub); background:#ece8dc; border-color:var(--line); }}

  .callout {{ display:flex; align-items:center; gap:12px; margin-top:14px;
              border:1px solid var(--line); border-left:4px solid var(--teal);
              background:var(--panel); padding:12px 16px; border-radius:4px; }}
  .callout .k {{ font-size:12px; color:var(--sub); }}
  .callout .badge {{ font-size:12px; font-weight:700; letter-spacing:.06em; padding:3px 10px;
                     border-radius:3px; text-transform:uppercase; }}
  .callout .badge.ok {{ color:var(--teal); background:var(--teal-bg); border:1px solid #bcd8cd; }}
  .callout .badge.no {{ color:var(--ox); background:var(--ox-bg); border:1px solid #dcc2be; }}
  .callout .hash {{ font-family:Consolas,monospace; font-size:12px; color:#3c4238; }}

  /* Desktop-style status footer */
  .statusbar {{ position:fixed; bottom:0; left:232px; right:0; height:26px;
                background:#2f403a; color:#bfd0c8; display:flex; align-items:center;
                gap:18px; padding:0 16px; font-size:11.5px; letter-spacing:.03em;
                border-top:1px solid #16211d; }}
  .statusbar .dot {{ width:7px; height:7px; border-radius:50%; background:#6fb8a6;
                     display:inline-block; margin-right:6px; }}
  .statusbar .sp {{ margin-left:auto; }}
</style>
</head>
<body>
<div class="app">
  <aside class="rail">
    <div class="brand">
      <div class="logo">
        <div class="mark">M</div>
        <div>
          <div class="name">MedTrust CIS</div>
          <div class="sys">Governance Console</div>
        </div>
      </div>
    </div>
    <nav>{_nav(active, counts)}</nav>
  </aside>

  <div>
    <div class="top">
      <div class="crumb">Workspace &nbsp;/&nbsp; <b>{_ROUTE_TO_TAB[active]}</b> &nbsp;/&nbsp; Session review</div>
      <div class="right">
        <span class="env">Prod · On-Prem</span>
        <div class="user"><div class="av">BP</div><span>B. Prathap · <b>Steward</b></span></div>
      </div>
    </div>

    <main>
      <div class="pagehead">
        <h1>{title}</h1>
        <div class="stamp">Session {now} · site <b>KGH-01</b></div>
      </div>
      <p class="lead">{lead}</p>
      {content}
    </main>

    <div class="statusbar">
      <span><span class="dot"></span>Connected · air-gapped</span>
      <span>Model pin: medtrust-ref · deterministic</span>
      <span>Egress: none</span>
      <span class="sp">© VeritasGraph · MedTrust CIS build 2026.09</span>
    </div>
  </div>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> RedirectResponse:
  return RedirectResponse(url="/access-governance", status_code=307)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
  return _render("dashboard")


@app.get("/access-governance", response_class=HTMLResponse)
def access_governance() -> str:
  return _render("access-governance")


@app.get("/retrieval-sources", response_class=HTMLResponse)
def retrieval_sources() -> str:
  return _render("retrieval-sources")


@app.get("/audit-ledger", response_class=HTMLResponse)
def audit_ledger() -> str:
  return _render("audit-ledger")


@app.get("/adverse-events", response_class=HTMLResponse)
def adverse_events() -> str:
  return _render("adverse-events")


@app.get("/pharmacovigilance", response_class=HTMLResponse)
def pharmacovigilance() -> str:
  return _render("pharmacovigilance")


@app.get("/policy-rules", response_class=HTMLResponse)
def policy_rules() -> str:
  return _render("policy-rules")


@app.get("/observability", response_class=HTMLResponse)
def observability() -> str:
  return _render("observability")


@app.get("/identity-iam", response_class=HTMLResponse)
def identity_iam() -> str:
  return _render("identity-iam")
