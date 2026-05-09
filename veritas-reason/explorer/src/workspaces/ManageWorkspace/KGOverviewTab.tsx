/**
 * src/workspaces/ManageWorkspace/KGOverviewTab.tsx
 *
 * Quick-view dashboard for the Knowledge Graph: node/edge counts,
 * type distributions, and top connected nodes.
 */
import { useState, useEffect, useCallback } from "react";
import { Network, RefreshCw, Loader2 } from "lucide-react";

interface KGStats {
  node_count: number;
  edge_count: number;
  node_types?: Record<string, number>;
  edge_types?: Record<string, number>;
  [key: string]: unknown;
}

interface NodeItem {
  id: string;
  type: string;
  content: string;
  properties?: Record<string, unknown>;
}

interface NodeListResponse {
  nodes: NodeItem[];
  total: number;
}

function TypeBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0" }}>
      <div style={{ width: 120, flexShrink: 0, color: "#c6d4e3", fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={label}>
        {label}
      </div>
      <div style={{ flex: 1, height: 6, borderRadius: 999, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            borderRadius: 999,
            background: color,
            transition: "width 400ms ease",
          }}
        />
      </div>
      <div style={{ width: 52, textAlign: "right", flexShrink: 0, display: "flex", gap: 6, justifyContent: "flex-end" }}>
        <span style={{ color: "#8b949e", fontSize: 11 }}>{count.toLocaleString()}</span>
        <span style={{ color: "#6a7f97", fontSize: 11 }}>{pct}%</span>
      </div>
    </div>
  );
}

const NODE_COLORS = ["#3E79F2", "#149287", "#2F9F61", "#555FD6", "#8A56D8", "#B65473", "#C9922E", "#4aa3ff", "#f2b66d"];
const EDGE_COLORS = ["#4cc38a", "#79c0ff", "#d2a8ff", "#f2b66d", "#ff7b72", "#58a6ff", "#4aa3ff", "#8A56D8"];

function buildTypeMap(nodes: NodeItem[], key: keyof NodeItem): Record<string, number> {
  const map: Record<string, number> = {};
  for (const node of nodes) {
    const val = String(node[key] ?? "unknown");
    map[val] = (map[val] ?? 0) + 1;
  }
  return map;
}

export function KGOverviewTab() {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [topNodes, setTopNodes] = useState<{ node: NodeItem; neighborCount: number }[]>([]);
  const [nodeTypeMap, setNodeTypeMap] = useState<Record<string, number>>({});

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [statsRes, nodesRes] = await Promise.all([
        fetch("/api/graph/stats"),
        fetch("/api/graph/nodes?limit=500"),
      ]);

      if (statsRes.ok) {
        const statsData: KGStats = await statsRes.json();
        setStats(statsData);
      }

      if (nodesRes.ok) {
        const nodesData: NodeListResponse = await nodesRes.json();
        const nodes = nodesData.nodes ?? [];
        setNodeTypeMap(buildTypeMap(nodes, "type"));

        // Simulate neighbor counts via edges fetch for top-N
        const edgesRes = await fetch("/api/graph/edges?limit=2000");
        if (edgesRes.ok) {
          const edgesData = await edgesRes.json();
          const edges: { source: string; target: string }[] = edgesData.edges ?? [];
          const degreeMap: Record<string, number> = {};
          for (const edge of edges) {
            degreeMap[edge.source] = (degreeMap[edge.source] ?? 0) + 1;
            degreeMap[edge.target] = (degreeMap[edge.target] ?? 0) + 1;
          }
          const sorted = nodes
            .map((n) => ({ node: n, neighborCount: degreeMap[n.id] ?? 0 }))
            .sort((a, b) => b.neighborCount - a.neighborCount)
            .slice(0, 10);
          setTopNodes(sorted);
        }
      }
    } catch {
      setError("Failed to load graph overview. Ensure the server is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchOverview();
  }, [fetchOverview]);

  const nodeTypeEntries = Object.entries(nodeTypeMap).sort((a, b) => b[1] - a[1]);
  const edgeTypeEntries = stats?.edge_types
    ? Object.entries(stats.edge_types).sort((a, b) => b[1] - a[1])
    : [];

  const totalNodes = stats?.node_count ?? 0;
  const totalEdges = stats?.edge_count ?? 0;

  return (
    <div style={shellStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Network size={18} color="#4aa3ff" />
          <div>
            <div style={{ color: "#ebf3ff", fontSize: 16, fontWeight: 700 }}>KG Overview</div>
            <div style={{ color: "#8b949e", fontSize: 12 }}>Quick view of the Knowledge Graph structure and health</div>
          </div>
        </div>
        <button onClick={() => void fetchOverview()} disabled={loading} style={refreshBtnStyle}>
          {loading ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
          <span>Refresh</span>
        </button>
      </div>

      {error ? (
        <div style={{ margin: "16px 24px", padding: "10px 14px", borderRadius: 10, background: "rgba(255,123,114,0.08)", border: "1px solid rgba(255,123,114,0.2)", color: "#ff7b72", fontSize: 13 }}>
          {error}
        </div>
      ) : null}

      <div style={scrollBodyStyle}>
        {/* Stats chips */}
        <div style={statsRowStyle}>
          {[
            { label: "Nodes", value: totalNodes.toLocaleString(), color: "#4aa3ff", sub: `${nodeTypeEntries.length} types` },
            { label: "Edges", value: totalEdges.toLocaleString(), color: "#4cc38a", sub: `${edgeTypeEntries.length} relationship types` },
            { label: "Density", value: totalNodes > 1 ? ((totalEdges / (totalNodes * (totalNodes - 1))) * 100).toFixed(3) + "%" : "—", color: "#d2a8ff", sub: "graph density" },
          ].map(({ label, value, color, sub }) => (
            <div key={label} style={statCardStyle}>
              <div style={{ color: "#8b949e", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{label}</div>
              <div style={{ color, fontSize: 28, fontWeight: 800, letterSpacing: "-0.04em", lineHeight: 1 }}>{loading ? "—" : value}</div>
              <div style={{ color: "#6a7f97", fontSize: 11, marginTop: 4 }}>{sub}</div>
            </div>
          ))}
        </div>

        {/* Type breakdowns */}
        <div style={sectionRowStyle}>
          {/* Node types */}
          <div style={breakdownCardStyle}>
            <div style={sectionTitleStyle}>Node Type Breakdown</div>
            {loading ? (
              <div style={skeletonWrapStyle}>
                {[80, 65, 45, 35, 25].map((w, i) => (
                  <div key={i} style={{ ...skeletonBarStyle, width: `${w}%` }} />
                ))}
              </div>
            ) : nodeTypeEntries.length === 0 ? (
              <div style={{ color: "#6a7f97", fontSize: 12 }}>No data — load the graph first.</div>
            ) : (
              nodeTypeEntries.slice(0, 8).map(([type, count], i) => (
                <TypeBar key={type} label={type} count={count} total={totalNodes || 1} color={NODE_COLORS[i % NODE_COLORS.length]} />
              ))
            )}
          </div>

          {/* Edge types */}
          <div style={breakdownCardStyle}>
            <div style={sectionTitleStyle}>Edge Type Breakdown</div>
            {loading ? (
              <div style={skeletonWrapStyle}>
                {[70, 55, 48, 30, 20].map((w, i) => (
                  <div key={i} style={{ ...skeletonBarStyle, width: `${w}%` }} />
                ))}
              </div>
            ) : edgeTypeEntries.length === 0 ? (
              <div style={{ color: "#6a7f97", fontSize: 12 }}>Edge type breakdown requires the stats endpoint to return edge_types.</div>
            ) : (
              edgeTypeEntries.slice(0, 8).map(([type, count], i) => (
                <TypeBar key={type} label={type} count={count} total={totalEdges || 1} color={EDGE_COLORS[i % EDGE_COLORS.length]} />
              ))
            )}
          </div>
        </div>

        {/* Top connected nodes */}
        {topNodes.length > 0 ? (
          <div style={breakdownCardStyle}>
            <div style={sectionTitleStyle}>Top Connected Nodes (by degree)</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 8, marginTop: 2 }}>
              {topNodes.map(({ node, neighborCount }, rank) => (
                <div key={node.id} style={topNodeRowStyle}>
                  <div style={{ color: "#6a7f97", fontSize: 12, fontWeight: 700, minWidth: 20 }}>#{rank + 1}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ color: "#e6edf3", fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {node.content || node.id}
                    </div>
                    <div style={{ color: "#8b949e", fontSize: 11 }}>{node.type}</div>
                  </div>
                  <div style={{ color: "#4aa3ff", fontSize: 12, fontWeight: 700, flexShrink: 0 }}>
                    {neighborCount} conn.
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

/* ─── styles ─────────────────────────────────────────────────────── */

const shellStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  width: "100%",
  height: "100%",
  background: "#0d1117",
  overflow: "hidden",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "20px 24px 16px",
  borderBottom: "1px solid rgba(88,166,255,0.1)",
  flexShrink: 0,
};

const refreshBtnStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "6px 12px",
  borderRadius: 8,
  border: "1px solid rgba(127,208,255,0.16)",
  background: "rgba(74,163,255,0.08)",
  color: "#8fa8c6",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
};

const scrollBodyStyle: React.CSSProperties = {
  flex: 1,
  overflowY: "auto",
  padding: "20px 24px",
  display: "flex",
  flexDirection: "column",
  gap: 16,
};

const statsRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: 12,
};

const statCardStyle: React.CSSProperties = {
  padding: "18px 20px",
  borderRadius: 16,
  background: "linear-gradient(135deg, rgba(13,17,23,0.8), rgba(22,27,34,0.5))",
  border: "1px solid rgba(127,208,255,0.1)",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)",
};

const sectionRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 12,
};

const breakdownCardStyle: React.CSSProperties = {
  padding: "16px 18px",
  borderRadius: 14,
  background: "linear-gradient(135deg, rgba(13,17,23,0.7), rgba(22,27,34,0.4))",
  border: "1px solid rgba(255,255,255,0.06)",
  display: "flex",
  flexDirection: "column",
  gap: 8,
};

const sectionTitleStyle: React.CSSProperties = {
  color: "#8b949e",
  fontSize: 11,
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.07em",
  marginBottom: 4,
};

const topNodeRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "8px 10px",
  borderRadius: 10,
  background: "rgba(255,255,255,0.025)",
  border: "1px solid rgba(255,255,255,0.05)",
};

const skeletonWrapStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 8,
  marginTop: 4,
};

const skeletonBarStyle: React.CSSProperties = {
  height: 12,
  borderRadius: 999,
  background: "rgba(255,255,255,0.05)",
  animation: "skeleton-pulse 1.4s ease-in-out infinite",
};
