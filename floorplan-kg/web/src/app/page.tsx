"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AssistPanel from "@/components/AssistPanel";
import GraphView from "@/components/GraphView";
import RoomsTable from "@/components/RoomsTable";
import SchedulesPanel from "@/components/SchedulesPanel";
import SummaryCards from "@/components/SummaryCards";
import TakeoffPanel from "@/components/TakeoffPanel";
import type { ExtractionResult, TakeoffLine } from "@/lib/types";

type Method = "pymupdf" | "pdfplumber";
type Tab = "overview" | "rooms" | "schedules" | "takeoff" | "graph" | "assist";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "rooms", label: "Rooms" },
  { id: "schedules", label: "Schedules" },
  { id: "takeoff", label: "Takeoff" },
  { id: "graph", label: "Knowledge Graph" },
  { id: "assist", label: "AI Assist" },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function Home() {
  const [method, setMethod] = useState<Method>("pymupdf");
  const [file, setFile] = useState<File | null>(null);
  const [sample, setSample] = useState("");
  const [samples, setSamples] = useState<Array<{ name: string; sizeBytes: number }>>([]);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [lines, setLines] = useState<TakeoffLine[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [exporting, setExporting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("/api/samples")
      .then((r) => r.json())
      .then((d) => setSamples(Array.isArray(d.items) ? d.items : []))
      .catch(() => setSamples([]));
  }, []);

  const run = useCallback(
    async (ceilingHeightFeet?: number) => {
      if (!file && !sample) {
        setError("Choose a PDF or pick a bundled sample first.");
        return;
      }
      setProcessing(true);
      setError(null);
      try {
        const form = new FormData();
        if (file) form.append("file", file);
        else form.append("sample", sample);
        form.append("method", method);
        if (ceilingHeightFeet) form.append("ceilingHeightFeet", String(ceilingHeightFeet));

        const res = await fetch("/api/process", { method: "POST", body: form });
        const payload = await res.json();
        if (!res.ok) {
          setError(payload.error ?? `Request failed with status ${res.status}`);
          setResult(null);
          return;
        }
        const extraction = payload as ExtractionResult;
        setResult(extraction);
        setLines(extraction.takeoff.lines);
      } catch (err) {
        setError(`Error processing PDF: ${err instanceof Error ? err.message : String(err)}`);
        setResult(null);
      } finally {
        setProcessing(false);
      }
    },
    [file, sample, method],
  );

  const exportFile = useCallback(
    async (target: string, format: "csv" | "xlsx", filename: string) => {
      if (!result) return;
      setExporting(true);
      setError(null);
      try {
        const res = await fetch("/api/export", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            format,
            target,
            filename,
            result,
            takeoff: { ...result.takeoff, lines },
          }),
        });
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}));
          setError(payload.error ?? `Export failed with status ${res.status}`);
          return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${filename.replace(/\.[a-z0-9]+$/i, "")}.${format}`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
      } catch (err) {
        setError(`Export failed: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setExporting(false);
      }
    },
    [result, lines],
  );

  return (
    <div className="shell">
      <header className="masthead">
        <h1 data-testid="app-title">📐 Floorplan Knowledge Graph &amp; Quantity Takeoff</h1>
        <p>
          Extract rooms, dimensions, symbols and schedule tables from an architectural floorplan
          PDF; assemble them into a provenance-tracked knowledge graph; derive a quantity takeoff
          you can edit by hand; export schedules and takeoffs to Excel or CSV. Runs entirely
          offline — no cloud OCR, no upload, no LLM required.
        </p>
      </header>

      <section className="panel" data-testid="input-panel">
        <h2>Input</h2>
        <div className="row">
          <div className="field">
            <label htmlFor="pdf-input">Upload a floorplan PDF</label>
            <input
              id="pdf-input"
              ref={fileInput}
              type="file"
              accept="application/pdf,.pdf"
              data-testid="file-input"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setSample("");
              }}
            />
          </div>

          <div className="field">
            <label htmlFor="sample-select">…or use a bundled sample</label>
            <select
              id="sample-select"
              data-testid="sample-select"
              value={sample}
              onChange={(e) => {
                setSample(e.target.value);
                setFile(null);
                if (fileInput.current) fileInput.current.value = "";
              }}
            >
              <option value="">— none —</option>
              {samples.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name} ({formatBytes(s.sizeBytes)})
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label id="method-label">Extraction backend</label>
            <fieldset className="radios" aria-labelledby="method-label">
              <label>
                <input
                  type="radio"
                  name="method"
                  value="pymupdf"
                  data-testid="method-pymupdf"
                  checked={method === "pymupdf"}
                  onChange={() => setMethod("pymupdf")}
                />
                PyMuPDF
              </label>
              <label>
                <input
                  type="radio"
                  name="method"
                  value="pdfplumber"
                  data-testid="method-pdfplumber"
                  checked={method === "pdfplumber"}
                  onChange={() => setMethod("pdfplumber")}
                />
                pdfplumber
              </label>
            </fieldset>
          </div>

          <button data-testid="run-extraction" disabled={processing} onClick={() => run()}>
            {processing ? (
              <>
                <span className="spinner" /> Extracting…
              </>
            ) : (
              "Build knowledge graph"
            )}
          </button>
        </div>

        {(file || sample) && (
          <p className="small muted" style={{ marginBottom: 0 }} data-testid="selected-input">
            Selected: <strong>{file ? file.name : sample}</strong>
            {file ? ` (${formatBytes(file.size)})` : ""}
          </p>
        )}
      </section>

      {processing && (
        <div className="alert info" data-testid="processing-banner">
          <span className="spinner" /> Processing PDF…
        </div>
      )}

      {error && (
        <div className="alert error" data-testid="error-banner" role="alert">
          {error}
        </div>
      )}

      {!result && !processing && (
        <div className="alert info" data-testid="empty-state">
          👆 Upload a PDF or pick a sample, then choose an extraction backend to get started.
        </div>
      )}

      {result && (
        <>
          <div className="alert ok" data-testid="success-banner">
            ✅ Extracted <strong>{result.metadata.originalFilename}</strong> with{" "}
            <strong data-testid="used-method">{result.metadata.processingMethod}</strong> in{" "}
            {result.metadata.durationMs.toFixed(0)} ms.
          </div>

          <nav className="tabs" role="tablist">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                data-testid={`tab-${t.id}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {tab === "overview" && (
            <section className="panel" data-testid="overview-panel">
              <h2>Extraction summary</h2>
              <SummaryCards result={result} />
              <table style={{ marginTop: 16 }} data-testid="metadata-table">
                <tbody>
                  {Object.entries(result.metadata).map(([key, value]) => (
                    <tr key={key}>
                      <td className="muted small" style={{ width: 200 }}>{key}</td>
                      <td className="mono small" data-testid={`meta-${key}`}>{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {tab === "rooms" && (
            <section className="panel">
              <h2>Rooms</h2>
              <RoomsTable result={result} />
            </section>
          )}

          {tab === "schedules" && (
            <section className="panel">
              <h2>Schedules</h2>
              <SchedulesPanel result={result} onExport={exportFile} exporting={exporting} />
            </section>
          )}

          {tab === "takeoff" && (
            <section className="panel">
              <h2>Quantity takeoff</h2>
              <TakeoffPanel
                lines={lines}
                onChange={setLines}
                onReset={() => setLines(result.takeoff.lines)}
                onExport={exportFile}
                exporting={exporting}
                assumptions={result.takeoff.assumptions}
                onAssumptionChange={(ceilingHeightFeet) => run(ceilingHeightFeet)}
              />
            </section>
          )}

          {tab === "graph" && (
            <section className="panel">
              <h2>Knowledge graph</h2>
              <GraphView result={result} />
            </section>
          )}

          {tab === "assist" && (
            <section>
              <AssistPanel result={result} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
