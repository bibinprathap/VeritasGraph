/**
 * src/workspaces/DecisionWorkspace/DecisionWorkspace.tsx
 */
import { useState, useEffect, useMemo } from "react";
import { Scale, Search } from "lucide-react";

const THEME_CSS = `
  .glass-panel {
    background: linear-gradient(135deg, rgba(13,17,23,0.75), rgba(22,27,34,0.6));
    backdrop-filter: blur(16px) saturate(1.2);
    -webkit-backdrop-filter: blur(16px) saturate(1.2);
    border: 1px solid rgba(88,166,255,0.2);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 1px 1px 0 rgba(255,255,255,0.05);
  }

  @keyframes skeleton-shimmer {
    0%   { opacity: 0.45; }
    50%  { opacity: 0.85; }
    100% { opacity: 0.45; }
  }
  .skeleton-item {
    border-radius: 8px;
    background: rgba(255,255,255,0.05);
    animation: skeleton-shimmer 1.4s ease-in-out infinite;
  }
`;

type OutcomeKind = "approved" | "rejected" | "deferred" | "pending" | string;

function outcomeStyle(outcome: string): { color: string; bg: string; border: string } {
  const lower = (outcome ?? "").toLowerCase();
  if (lower.includes("approv") || lower.includes("accept"))
    return { color: "#4cc38a", bg: "rgba(76,195,138,0.12)", border: "rgba(76,195,138,0.28)" };
  if (lower.includes("reject") || lower.includes("denied") || lower.includes("fail"))
    return { color: "#ff7b72", bg: "rgba(255,123,114,0.12)", border: "rgba(255,123,114,0.28)" };
  if (lower.includes("defer") || lower.includes("pending") || lower.includes("review"))
    return { color: "#f2b66d", bg: "rgba(242,182,109,0.12)", border: "rgba(242,182,109,0.28)" };
  return { color: "#8fa8c6", bg: "rgba(143,168,198,0.08)", border: "rgba(143,168,198,0.18)" };
}

function OutcomeBadge({ outcome }: { outcome: OutcomeKind }) {
  const style = outcomeStyle(outcome);
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 10,
        fontWeight: 800,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: style.color,
        background: style.bg,
        border: `1px solid ${style.border}`,
      }}
    >
      {outcome || "unknown"}
    </span>
  );
}

function SkeletonList() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="skeleton-item" style={{ height: 62 }} />
      ))}
    </div>
  );
}

/* ─── Causal Flow Diagram ──────────────────────────────────────────── */

interface ChainStep {
  id: string;
  relationship: string;
  content?: string;
  type?: string;
  [key: string]: unknown;
}

function RelationshipPill({ label }: { label: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0, position: "relative", margin: "0 auto" }}>
      {/* Connector line top */}
      <div style={{ width: 2, height: 12, background: "rgba(88,166,255,0.25)" }} />
      {/* Pill */}
      <div
        style={{
          padding: "3px 10px",
          borderRadius: 999,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "#79c0ff",
          background: "rgba(88,166,255,0.1)",
          border: "1px solid rgba(88,166,255,0.22)",
          whiteSpace: "nowrap",
          maxWidth: 260,
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
        title={label}
      >
        {label}
      </div>
      {/* Connector line bottom + arrow */}
      <div style={{ width: 2, height: 10, background: "rgba(88,166,255,0.25)" }} />
      <div style={{ width: 0, height: 0, borderLeft: "5px solid transparent", borderRight: "5px solid transparent", borderTop: "6px solid rgba(88,166,255,0.4)" }} />
    </div>
  );
}

function ChainNodeCard({ step, index }: { step: ChainStep; index: number }) {
  const COLORS = ["#3E79F2", "#149287", "#2F9F61", "#555FD6", "#8A56D8", "#B65473", "#C9922E", "#4aa3ff"];
  const color = COLORS[index % COLORS.length];

  return (
    <div
      style={{
        position: "relative",
        padding: "14px 16px",
        borderRadius: 12,
        background: "linear-gradient(135deg, rgba(13,17,23,0.75), rgba(22,27,34,0.5))",
        border: `1px solid ${color}33`,
        boxShadow: `0 0 0 1px ${color}11, inset 0 1px 0 rgba(255,255,255,0.04)`,
        borderLeft: `3px solid ${color}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span
          style={{
            width: 8, height: 8, borderRadius: "50%",
            background: color,
            boxShadow: `0 0 8px ${color}`,
            flexShrink: 0,
          }}
        />
        {step.type ? (
          <span
            style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
              textTransform: "uppercase", color,
            }}
          >
            {step.type}
          </span>
        ) : null}
      </div>
      <div style={{ color: "#e6edf3", fontSize: 14, fontWeight: 600 }}>
        {step.content || step.id}
      </div>
      {step.id && step.id !== step.content ? (
        <div style={{ color: "#6a7f97", fontSize: 11, fontFamily: "monospace", marginTop: 3 }}>{step.id}</div>
      ) : null}
    </div>
  );
}

function CausalFlowDiagram({ chain, loading }: { chain: ChainStep[]; loading: boolean }) {
  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton-item" style={{ height: 68 }} />
        ))}
      </div>
    );
  }

  if (chain.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "40px 24px", color: "#8b949e", fontSize: 13 }}>
        No causal chain steps found for this decision.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "stretch" }}>
      {chain.map((step, index) => (
        <div key={`${step.id}-${index}`} style={{ display: "flex", flexDirection: "column" }}>
          <ChainNodeCard step={step} index={index} />
          {index < chain.length - 1 ? (
            <RelationshipPill label={chain[index + 1]?.relationship || "→"} />
          ) : null}
        </div>
      ))}
    </div>
  );
}

/* ─── Main Workspace ──────────────────────────────────────────────── */

export function DecisionWorkspace() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<any | null>(null);
  const [chain, setChain] = useState<ChainStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [filterQuery, setFilterQuery] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setListLoading(true);
    fetch("/api/decisions", { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load decisions: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setDecisions(data);
        if (data.length > 0) void handleSelectDecision(data[0]);
      })
      .catch((err) => { if (err.name !== "AbortError") console.error(err); })
      .finally(() => setListLoading(false));
    return () => controller.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredDecisions = useMemo(() => {
    if (!filterQuery.trim()) return decisions;
    const q = filterQuery.toLowerCase();
    return decisions.filter(
      (d) =>
        String(d.decision_id ?? "").toLowerCase().includes(q) ||
        String(d.category ?? "").toLowerCase().includes(q) ||
        String(d.outcome ?? "").toLowerCase().includes(q),
    );
  }, [decisions, filterQuery]);

  const handleSelectDecision = async (d: any) => {
    setSelectedDecision(d);
    setLoading(true);
    setChain([]);
    const controller = new AbortController();
    try {
      const res = await fetch(`/api/decisions/${encodeURIComponent(d.decision_id)}/chain`, { signal: controller.signal });
      if (!res.ok) throw new Error(`Failed to load chain: ${res.status}`);
      const data = await res.json();
      setChain(data.chain || []);
    } catch (e) {
      if ((e as DOMException).name !== "AbortError") console.error(e);
    } finally {
      setLoading(false);
    }
    return () => controller.abort();
  };

  return (
    <div style={{ display: "flex", width: "100%", height: "100%", background: "#0d1117", overflow: "hidden" }}>
      <style>{THEME_CSS}</style>

      {/* Left Column — Decision List */}
      <div
        className="glass-panel"
        style={{
          width: 300,
          display: "flex",
          flexDirection: "column",
          borderRadius: 0,
          border: "none",
          borderRight: "1px solid rgba(88,166,255,0.16)",
        }}
      >
        {/* List header */}
        <div style={{ padding: "20px 20px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Scale size={16} color="#4aa3ff" />
            <h2 style={{ color: "#ebf3ff", margin: 0, fontSize: 15, fontWeight: 700 }}>Decisions</h2>
            {decisions.length > 0 ? (
              <span style={{ color: "#6a7f97", fontSize: 11, marginLeft: "auto" }}>{decisions.length}</span>
            ) : null}
          </div>

          {/* Filter input */}
          <div style={{ position: "relative" }}>
            <Search
              size={13}
              color="#8b949e"
              style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
            />
            <input
              type="text"
              placeholder="Filter decisions…"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              style={filterInputStyle}
            />
          </div>
        </div>

        {/* Decision list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px" }}>
          {listLoading ? (
            <SkeletonList />
          ) : filteredDecisions.length === 0 ? (
            <div style={{ color: "#6a7f97", fontSize: 13, textAlign: "center", padding: "32px 12px" }}>
              {decisions.length === 0 ? "No decisions available." : "No decisions match your filter."}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {filteredDecisions.map((d) => {
                const isActive = selectedDecision?.decision_id === d.decision_id;
                return (
                  <button
                    key={d.decision_id}
                    onClick={() => void handleSelectDecision(d)}
                    style={{
                      textAlign: "left",
                      padding: "10px 12px",
                      borderRadius: 10,
                      cursor: "pointer",
                      background: isActive
                        ? "rgba(74,163,255,0.15)"
                        : "rgba(255,255,255,0.02)",
                      border: isActive
                        ? "1px solid rgba(74,163,255,0.32)"
                        : "1px solid rgba(255,255,255,0.06)",
                      color: isActive ? "#ffffff" : "#c6d4e3",
                      transition: "all 160ms ease",
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{d.decision_id}</div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                      {d.category ? (
                        <span style={{ fontSize: 11, color: "#8b949e" }}>{d.category}</span>
                      ) : null}
                      {d.outcome ? <OutcomeBadge outcome={d.outcome} /> : null}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right Column — Decision Detail */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Radial accent */}
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at top right, rgba(88,166,255,0.04), transparent 55%)", pointerEvents: "none", zIndex: 0 }} />

        {selectedDecision ? (
          <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px", position: "relative", zIndex: 1 }}>
            {/* Decision header */}
            <div style={{ marginBottom: 28 }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 14, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ color: "#8b949e", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 6 }}>
                    Decision ID
                  </div>
                  <h1 style={{ color: "#ffffff", fontSize: 24, fontWeight: 800, letterSpacing: "-0.03em", margin: "0 0 8px 0", wordBreak: "break-word" }}>
                    {selectedDecision.decision_id}
                  </h1>
                </div>
                {selectedDecision.outcome ? <OutcomeBadge outcome={selectedDecision.outcome} /> : null}
              </div>

              {selectedDecision.category ? (
                <div style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 10px", borderRadius: 999, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#8b949e", fontSize: 12 }}>
                  {selectedDecision.category}
                </div>
              ) : null}
            </div>

            {/* Causal Chain */}
            <div className="glass-panel" style={{ padding: 24, borderRadius: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "linear-gradient(135deg, #4aa3ff, #f2b66d)", boxShadow: "0 0 10px rgba(74,163,255,0.4)" }} />
                <h3 style={{ color: "#e6edf3", margin: 0, fontSize: 14, fontWeight: 700, letterSpacing: "0.02em" }}>
                  Causal Chain
                </h3>
                {chain.length > 0 && !loading ? (
                  <span style={{ color: "#6a7f97", fontSize: 11, marginLeft: "auto" }}>
                    {chain.length} step{chain.length !== 1 ? "s" : ""}
                  </span>
                ) : null}
              </div>
              <CausalFlowDiagram chain={chain} loading={loading} />
            </div>
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#8b949e", fontSize: 14 }}>
            Select a decision to inspect its causal chain.
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── styles ─────────────────────────────────────────────────────── */

const filterInputStyle: React.CSSProperties = {
  width: "100%",
  padding: "7px 10px 7px 30px",
  background: "rgba(0,0,0,0.25)",
  border: "1px solid rgba(88,166,255,0.16)",
  borderRadius: 8,
  color: "#c6d4e3",
  fontSize: 12,
  outline: "none",
  boxSizing: "border-box",
};
