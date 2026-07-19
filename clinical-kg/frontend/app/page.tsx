"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Assertion, Fact, GraphData, Match } from "./lib/api";
import GraphView from "./components/GraphView";

type Tab = "query" | "ingest" | "patients" | "contradictions" | "graph" | "risk";

const EXAMPLE_QUERIES = [
  "List patients with T2DM taking metformin whose most recent eGFR < 30",
  "patients with hypertension",
  "patients with atrial fibrillation taking warfarin",
  "patients with diabetes and HbA1c > 8",
];

function Badge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{value}</span>;
}

function Citations({ items }: { items: string[] }) {
  return (
    <span>
      {items.map((c) => (
        <span className="chip" key={c}>
          {c}
        </span>
      ))}
    </span>
  );
}

export default function Page() {
  const [tab, setTab] = useState<Tab>("query");
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api.health());
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  const withLoading = async (fn: () => Promise<void>) => {
    setLoading(true);
    setError(null);
    try {
      await fn();
      await refreshHealth();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const stats = health?.stats;

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <div className="logo">KG</div>
          <div>
            <h1>Clinical Knowledge Graph</h1>
            <p>
              HIPAA-safe · on-device de-identification · contradiction detection ·
              multi-hop cohort queries with citations
            </p>
          </div>
        </div>
        <div className="row">
          <span className={`pill ${health ? "ok" : ""}`}>
            {health ? "API connected" : "API offline"}
          </span>
          <button
            className="ghost"
            onClick={() => withLoading(async () => void (await api.loadSamples()))}
            disabled={loading}
          >
            Load sample notes
          </button>
          <button
            className="ghost"
            onClick={() => withLoading(async () => void (await api.reset()))}
            disabled={loading}
          >
            Reset
          </button>
        </div>
      </header>

      {stats && (
        <div className="stat-row">
          <div className="stat">
            <div className="n">{stats.by_type?.Patient ?? 0}</div>
            <div className="l">Patients</div>
          </div>
          <div className="stat">
            <div className="n">{stats.by_type?.Condition ?? 0}</div>
            <div className="l">Conditions</div>
          </div>
          <div className="stat">
            <div className="n">{stats.by_type?.Medication ?? 0}</div>
            <div className="l">Medications</div>
          </div>
          <div className="stat">
            <div className="n">{stats.by_type?.LabResult ?? 0}</div>
            <div className="l">Lab results</div>
          </div>
          <div className="stat">
            <div className="n">{stats.nodes}</div>
            <div className="l">Graph nodes</div>
          </div>
          <div className="stat">
            <div className="n">{stats.edges}</div>
            <div className="l">Graph edges</div>
          </div>
        </div>
      )}

      {error && (
        <p style={{ color: "var(--red)" }}>Error: {error}</p>
      )}

      <div className="tabs" style={{ marginTop: 18 }}>
        {(
          [
            ["query", "Cohort Query"],
            ["ingest", "Ingest Note"],
            ["patients", "Patients"],
            ["contradictions", "Contradictions"],
            ["graph", "Graph"],
            ["risk", "Re-ID Risk"],
          ] as [Tab, string][]
        ).map(([t, label]) => (
          <div
            key={t}
            className={`tab ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {label}
          </div>
        ))}
      </div>

      {tab === "query" && <QueryTab />}
      {tab === "ingest" && <IngestTab onDone={refreshHealth} />}
      {tab === "patients" && <PatientsTab />}
      {tab === "contradictions" && <ContradictionsTab />}
      {tab === "graph" && <GraphTab />}
      {tab === "risk" && <RiskTab />}
    </div>
  );
}

function QueryTab() {
  const [q, setQ] = useState(EXAMPLE_QUERIES[0]);
  const [res, setRes] = useState<{ parsed: any; matches: Match[]; match_count: number } | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.query(q));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>Multi-hop cohort query</h2>
        <p className="sub">
          Natural language is parsed into structured conditions, medications, and
          lab thresholds, then executed as a graph traversal. Every match is
          backed by span-level <span className="chip">[doc#chunk]</span> citations.
        </p>
        <textarea rows={2} value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="action" onClick={run} disabled={busy}>
            {busy ? "Running…" : "Run query"}
          </button>
          <span className="muted">Examples:</span>
          {EXAMPLE_QUERIES.map((ex) => (
            <span key={ex} className="example-q" onClick={() => setQ(ex)}>
              {ex.length > 42 ? ex.slice(0, 41) + "…" : ex}
            </span>
          ))}
        </div>
        {err && <p style={{ color: "var(--red)" }}>{err}</p>}
      </div>

      {res && (
        <div className="card">
          <h2>{res.match_count} matching patient(s)</h2>
          <p className="sub">
            Parsed → conditions: {res.parsed.conditions.join(", ") || "—"} · meds:{" "}
            {res.parsed.medications.join(", ") || "—"} · labs:{" "}
            {res.parsed.lab_filters
              .map((f: any) => `${f.display} ${f.op} ${f.value}`)
              .join(", ") || "—"}
          </p>
          {res.matches.map((m) => (
            <div className="match" key={m.patient_id}>
              <h3>Patient {m.patient_id}</h3>
              <ul className="reasons">
                {m.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
              <div style={{ marginTop: 8 }}>
                <Citations items={m.citations} />
              </div>
            </div>
          ))}
          {res.match_count === 0 && (
            <p className="muted">
              No patients matched. Load sample notes or ingest data first.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

const SAMPLE_NOTE = `Patient: Jane Doe    MRN: 3391002    Phone: (312) 555-0198
Date of Service: 06/01/2025

HPI: Patient denies any history of diabetes. Reports increased thirst.

Problem List:
1. Type 2 diabetes mellitus, on metformin 500mg BID.
2. Hypertension on lisinopril 10mg daily.

Labs: eGFR 27 mL/min. HbA1c 8.9%. Creatinine 2.1 mg/dL.

Assessment and Plan: Type 2 diabetes mellitus with CKD. Hold metformin if eGFR < 30.`;

function IngestTab({ onDone }: { onDone: () => void }) {
  const [text, setText] = useState(SAMPLE_NOTE);
  const [patientId, setPatientId] = useState("P100");
  const [docId, setDocId] = useState("note-user-1");
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await api.ingest([
        { doc_id: docId, patient_id: patientId, text },
      ]);
      setResult(r.ingested[0]);
      onDone();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>Ingest a clinical note</h2>
        <p className="sub">
          De-identify (Safe Harbor) → extract entities → reconcile assertions
          with contradiction detection → load into the graph. Runs 100% on-prem.
        </p>
        <div className="row" style={{ marginBottom: 10 }}>
          <input
            type="text"
            style={{ maxWidth: 180 }}
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            placeholder="patient_id"
          />
          <input
            type="text"
            style={{ maxWidth: 220 }}
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            placeholder="doc_id"
          />
        </div>
        <textarea rows={14} value={text} onChange={(e) => setText(e.target.value)} />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="action" onClick={run} disabled={busy}>
            {busy ? "Ingesting…" : "Ingest note"}
          </button>
        </div>
        {err && <p style={{ color: "var(--red)" }}>{err}</p>}
      </div>

      {result && (
        <div className="card">
          <h2>Ingestion result</h2>
          <p className="sub">
            {result.phi_redactions} PHI element(s) redacted · vault{" "}
            <span className="chip">{result.vault_id.slice(0, 10)}…</span>
          </p>
          <table>
            <thead>
              <tr>
                <th>Concept</th>
                <th>Code</th>
                <th>Axes</th>
                <th>Citations</th>
              </tr>
            </thead>
            <tbody>
              {result.assertions.map((a: Assertion, i: number) => (
                <tr key={i}>
                  <td>
                    {a.display}
                    {a.contradiction && (
                      <>
                        {" "}
                        <span className="badge contradiction">contradiction</span>
                      </>
                    )}
                  </td>
                  <td className="muted">
                    {a.system}:{a.code}
                  </td>
                  <td>
                    <Badge value={a.negation} />{" "}
                    {a.certainty === "uncertain" && <Badge value="uncertain" />}{" "}
                    {a.temporality === "historical" && <Badge value="historical" />}{" "}
                    {a.experiencer === "other" && <Badge value="other" />}
                  </td>
                  <td>
                    <Citations items={a.citations} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PatientsTab() {
  const [data, setData] = useState<{ patient_id: string; facts: Fact[] }[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .patients()
      .then((r) => setData(r.patients))
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="card">Error: {err}</div>;
  if (!data.length)
    return (
      <div className="card">
        <p className="muted">No patients. Load sample notes first.</p>
      </div>
    );

  return (
    <div className="grid">
      {data.map((p) => (
        <div className="card" key={p.patient_id}>
          <h2>Patient {p.patient_id}</h2>
          <p className="sub">{p.facts.length} clinical fact(s)</p>
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Concept</th>
                <th>Detail</th>
                <th>Axes</th>
                <th>Citations</th>
              </tr>
            </thead>
            <tbody>
              {p.facts.map((f, i) => (
                <tr key={i}>
                  <td className="muted">{f.ntype}</td>
                  <td>
                    {f.display}
                    {f.contradiction && (
                      <>
                        {" "}
                        <span className="badge contradiction">!</span>
                      </>
                    )}
                  </td>
                  <td className="muted">
                    {[f.dose, f.frequency, f.route, f.value, f.unit]
                      .filter(Boolean)
                      .join(" ") || "—"}
                  </td>
                  <td>
                    <Badge value={f.negation} />
                  </td>
                  <td>
                    <Citations items={f.citations} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function ContradictionsTab() {
  const [data, setData] = useState<
    (Assertion & { patient_id: string; doc_id: string })[]
  >([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .contradictions()
      .then((r) => setData(r.contradictions))
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="card">Error: {err}</div>;

  return (
    <div className="card">
      <h2>Reconciliation contradictions</h2>
      <p className="sub">
        Where affirmed and negated evidence coexist for the same concept. Section
        authority resolves the status; both conflicting spans are preserved for
        clinician review.
      </p>
      {!data.length && <p className="muted">No contradictions found.</p>}
      {data.map((c, i) => (
        <div className="match" key={i}>
          <h3>
            Patient {c.patient_id} · {c.display}{" "}
            <span className="badge contradiction">contradiction</span>
          </h3>
          <p className="muted" style={{ margin: "4px 0" }}>
            Resolved status: <Badge value={c.negation} /> (highest-authority section wins)
          </p>
          <table>
            <thead>
              <tr>
                <th>Section</th>
                <th>Evidence text</th>
                <th>Citation</th>
              </tr>
            </thead>
            <tbody>
              {c.conflicting_spans.map((s, j) => (
                <tr key={j}>
                  <td className="muted">{s.section || "—"}</td>
                  <td>{s.text}</td>
                  <td>
                    <span className="chip">{s.citation}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function GraphTab() {
  const [data, setData] = useState<GraphData>({ nodes: [], edges: [] });
  const [patients, setPatients] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.patients().then((r) => setPatients(r.patients.map((p) => p.patient_id)));
  }, []);

  useEffect(() => {
    api
      .graph(selected || undefined)
      .then(setData)
      .catch((e) => setErr(e.message));
  }, [selected]);

  return (
    <div className="card">
      <h2>Knowledge graph</h2>
      <p className="sub">
        Patient → clinical facts → canonical concepts → provenance spans. Layered
        left to right.
      </p>
      <div className="row" style={{ marginBottom: 12 }}>
        <span className="muted">Focus:</span>
        <button
          className={`tab ${selected === "" ? "active" : ""}`}
          onClick={() => setSelected("")}
        >
          All
        </button>
        {patients.map((p) => (
          <button
            key={p}
            className={`tab ${selected === p ? "active" : ""}`}
            onClick={() => setSelected(p)}
          >
            {p}
          </button>
        ))}
      </div>
      {err && <p style={{ color: "var(--red)" }}>{err}</p>}
      <GraphView data={data} />
      <div className="legend">
        {[
          ["Patient", "#12b3a6"],
          ["Condition", "#f5b942"],
          ["Medication", "#c39bff"],
          ["LabResult", "#45c17a"],
          ["Concept", "#5a6b8c"],
          ["Span", "#3a4a6b"],
        ].map(([l, c]) => (
          <span key={l}>
            <span className="dot" style={{ background: c }} />
            {l}
          </span>
        ))}
      </div>
    </div>
  );
}

const DEFAULT_RECORDS = JSON.stringify(
  [
    { zip3: "021", age_band: "60-70", sex: "M" },
    { zip3: "021", age_band: "60-70", sex: "M" },
    { zip3: "021", age_band: "60-70", sex: "M" },
    { zip3: "021", age_band: "60-70", sex: "M" },
    { zip3: "021", age_band: "60-70", sex: "M" },
    { zip3: "980", age_band: "40-50", sex: "F" },
  ],
  null,
  2
);

function RiskTab() {
  const [records, setRecords] = useState(DEFAULT_RECORDS);
  const [quasi, setQuasi] = useState("zip3, age_band, sex");
  const [targetK, setTargetK] = useState(5);
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setErr(null);
    try {
      const recs = JSON.parse(records);
      const q = quasi.split(",").map((s) => s.trim()).filter(Boolean);
      setRes(await api.kAnonymity(recs, q, targetK));
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>Re-identification risk (k-anonymity)</h2>
        <p className="sub">
          Before releasing a cohort, verify every quasi-identifier combination is
          shared by at least <b>k</b> patients (target k ≥ 5 for USA Safe Harbor
          releases).
        </p>
        <div className="row" style={{ marginBottom: 10 }}>
          <input
            type="text"
            style={{ maxWidth: 320 }}
            value={quasi}
            onChange={(e) => setQuasi(e.target.value)}
            placeholder="quasi-identifiers (comma-separated)"
          />
          <input
            type="text"
            style={{ maxWidth: 100 }}
            value={targetK}
            onChange={(e) => setTargetK(Number(e.target.value) || 1)}
            placeholder="target k"
          />
        </div>
        <textarea
          rows={12}
          value={records}
          onChange={(e) => setRecords(e.target.value)}
        />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="action" onClick={run}>
            Compute k-anonymity
          </button>
        </div>
        {err && <p style={{ color: "var(--red)" }}>{err}</p>}
      </div>

      {res && (
        <div className="card">
          <h2>
            k = {res.k}{" "}
            {res.satisfied ? (
              <span className="badge affirmed">satisfies k ≥ {res.target_k}</span>
            ) : (
              <span className="badge negated">violates k ≥ {res.target_k}</span>
            )}
          </h2>
          <p className="sub">
            {res.equivalence_classes} equivalence class(es) ·{" "}
            {res.violating_groups.length} violating
          </p>
          {res.violating_groups.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Quasi-identifiers</th>
                  <th>Group size</th>
                </tr>
              </thead>
              <tbody>
                {res.violating_groups.map((g: any, i: number) => (
                  <tr key={i}>
                    <td className="muted">
                      {Object.entries(g.quasi_identifiers)
                        .map(([k, v]) => `${k}=${v}`)
                        .join(", ")}
                    </td>
                    <td>{g.size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
