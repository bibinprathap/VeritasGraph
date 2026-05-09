import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

const SAMPLE_FACTS = `inhibits(Metformin, mTOR)\ncauses(mTOR, Neurodegeneration)`;
const SAMPLE_RULE = `IF inhibits(Metformin, mTOR) AND causes(mTOR, Neurodegeneration) THEN candidate(Metformin, Alzheimer's)`;

export function ReasoningWorkspace() {
  const queryClient = useQueryClient();
  const [facts, setFacts] = useState(SAMPLE_FACTS);
  const [rules, setRules] = useState(SAMPLE_RULE);
  const [applyToGraph, setApplyToGraph] = useState(true);
  const [result, setResult] = useState<{ inferred_facts?: string[]; rules_fired?: number; added_edges?: number; mutated?: boolean } | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");

  async function handleRun() {
    setIsRunning(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/reason", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          facts: facts.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
          rules: rules.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
          mode: "forward",
          apply_to_graph: applyToGraph,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Reasoning failed with status ${response.status}`);
      }
      setResult(data);
      if (data.mutated) {
        queryClient.invalidateQueries({ queryKey: ["graph", "full-load"] });
      }
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Reasoning failed");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 24, height: "100%", padding: 24, boxSizing: "border-box", background: "#0d1117" }}>
      <div style={panelStyle}>
        <h3 style={titleStyle}>Facts</h3>
        <p style={copyStyle}>Enter one fact per line using `predicate(subject, object)` form.</p>
        <textarea value={facts} onChange={(event) => setFacts(event.target.value)} style={textareaStyle} />

        <h3 style={{ ...titleStyle, marginTop: 18 }}>Rules</h3>
        <p style={copyStyle}>Write rules in `IF ... AND ... THEN ...` format. If the advanced reasoner is unavailable, the explorer falls back to an internal rule matcher for this format.</p>
        <textarea value={rules} onChange={(event) => setRules(event.target.value)} style={{ ...textareaStyle, minHeight: 160 }} />

        <label style={{ display: "flex", alignItems: "center", gap: 10, color: "#c9d1d9", fontSize: 13, marginTop: 16 }}>
          <input type="checkbox" checked={applyToGraph} onChange={(event) => setApplyToGraph(event.target.checked)} />
          Write inferred binary facts back into the graph as inferred edges
        </label>

        <button onClick={handleRun} disabled={isRunning} style={runButtonStyle}>
          {isRunning ? "Running..." : "Run Reasoning"}
        </button>
      </div>

      <div style={panelStyle}>
        <h3 style={titleStyle}>Inference Results</h3>

        {error ? <div style={{ color: "#ff7b72", marginBottom: 12 }}>{error}</div> : null}

        {result ? (
          <>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
              <span style={pillStyle}>rules fired: {result.rules_fired ?? 0}</span>
              <span style={pillStyle}>edges added: {result.added_edges ?? 0}</span>
              <span style={pillStyle}>{result.mutated ? "graph updated" : "preview only"}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(result.inferred_facts || []).length ? (
                result.inferred_facts?.map((fact) => (
                  <div key={fact} style={factCardStyle}>{fact}</div>
                ))
              ) : (
                <div style={{ color: "#8b949e", fontSize: 13 }}>No inferred facts were produced.</div>
              )}
            </div>
          </>
        ) : (
          <div style={{ color: "#8b949e", fontSize: 13 }}>Run a rule set to inspect inferred statements here.</div>
        )}
      </div>
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, rgba(13, 17, 23, 0.78), rgba(22, 27, 34, 0.64))",
  border: "1px solid rgba(88, 166, 255, 0.18)",
  borderRadius: 16,
  padding: 20,
  display: "flex",
  flexDirection: "column",
};

const titleStyle: React.CSSProperties = {
  color: "#fff",
  margin: 0,
  fontSize: 18,
  fontWeight: 700,
};

const copyStyle: React.CSSProperties = {
  color: "#8b949e",
  fontSize: 13,
  lineHeight: 1.5,
  margin: "8px 0 14px",
};

const textareaStyle: React.CSSProperties = {
  width: "100%",
  minHeight: 120,
  resize: "vertical",
  borderRadius: 12,
  border: "1px solid rgba(88, 166, 255, 0.18)",
  background: "rgba(0, 0, 0, 0.25)",
  color: "#e6edf3",
  padding: 12,
  fontFamily: "Consolas, monospace",
  fontSize: 13,
  boxSizing: "border-box",
};

const runButtonStyle: React.CSSProperties = {
  marginTop: 18,
  border: "1px solid rgba(88, 166, 255, 0.3)",
  background: "rgba(31, 111, 235, 0.2)",
  color: "#fff",
  borderRadius: 12,
  padding: "11px 14px",
  fontWeight: 700,
  cursor: "pointer",
};

const pillStyle: React.CSSProperties = {
  color: "#79c0ff",
  border: "1px solid rgba(88, 166, 255, 0.2)",
  background: "rgba(88, 166, 255, 0.08)",
  borderRadius: 999,
  padding: "5px 10px",
  fontSize: 12,
};

const factCardStyle: React.CSSProperties = {
  color: "#e6edf3",
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.06)",
  borderRadius: 10,
  padding: "10px 12px",
  fontFamily: "Consolas, monospace",
  fontSize: 13,
};
