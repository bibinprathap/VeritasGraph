"use client";

import { useMemo, useState } from "react";
import type { ExtractionResult, GraphNode } from "@/lib/types";

const TYPE_COLORS: Record<string, string> = {
  Document: "#f0883e",
  Sheet: "#8957e5",
  Room: "#4f9dff",
  Opening: "#3fb950",
  OpeningType: "#238636",
  DoorType: "#1f6feb",
  Fixture: "#db6d28",
  Assembly: "#a371f7",
  Schedule: "#d29922",
  ScheduleRow: "#bb8009",
  AreaCallout: "#39c5cf",
};

// Columns run left to right in roughly the order the graph is built, so the
// picture reads as a pipeline rather than a hairball.
const COLUMN_ORDER = [
  "Document", "Sheet", "Room", "Fixture", "Opening", "OpeningType",
  "Assembly", "AreaCallout", "Schedule", "ScheduleRow", "DoorType",
];

const MAX_RENDERED = 400;

function colorFor(type: string): string {
  return TYPE_COLORS[type] ?? "#8b949e";
}

export default function GraphView({ result }: { result: ExtractionResult }) {
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const types = useMemo(
    () => Object.keys(result.graph.stats.nodesByType).sort(
      (a, b) => COLUMN_ORDER.indexOf(a) - COLUMN_ORDER.indexOf(b),
    ),
    [result],
  );

  const { positions, nodes, edges, truncated, width, height } = useMemo(() => {
    const visibleNodes = result.graph.nodes.filter((n) => !hidden.has(n.type));
    const capped = visibleNodes.slice(0, MAX_RENDERED);
    const ids = new Set(capped.map((n) => n.id));

    const columns = new Map<string, GraphNode[]>();
    for (const node of capped) {
      const list = columns.get(node.type) ?? [];
      list.push(node);
      columns.set(node.type, list);
    }
    const ordered = [...columns.keys()].sort(
      (a, b) => COLUMN_ORDER.indexOf(a) - COLUMN_ORDER.indexOf(b),
    );

    const colGap = 150;
    const rowGap = 24;
    const tallest = Math.max(1, ...ordered.map((t) => (columns.get(t) ?? []).length));
    const pos = new Map<string, { x: number; y: number }>();

    ordered.forEach((type, colIndex) => {
      const list = columns.get(type) ?? [];
      const columnHeight = (list.length - 1) * rowGap;
      const top = ((tallest - 1) * rowGap - columnHeight) / 2;
      list.forEach((node, i) => {
        pos.set(node.id, { x: 70 + colIndex * colGap, y: 50 + top + i * rowGap });
      });
    });

    return {
      positions: pos,
      nodes: capped,
      edges: result.graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target)),
      truncated: visibleNodes.length - capped.length,
      width: Math.max(360, 70 + ordered.length * colGap),
      height: Math.max(220, 100 + (tallest - 1) * rowGap),
    };
  }, [result, hidden]);

  function toggleType(type: string) {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  return (
    <div data-testid="graph-panel">
      <div className="spread" style={{ marginBottom: 10 }}>
        <span className="small muted" data-testid="graph-stats">
          {result.graph.stats.nodeCount} nodes · {result.graph.stats.edgeCount} edges ·{" "}
          {nodes.length} rendered
        </span>
        <span className="small muted">Click a node to inspect its provenance.</span>
      </div>

      <div className="legend" data-testid="graph-legend">
        {types.map((type) => (
          <button
            key={type}
            className="secondary"
            style={{ padding: "3px 9px", fontSize: 12, opacity: hidden.has(type) ? 0.4 : 1 }}
            aria-pressed={!hidden.has(type)}
            data-testid="graph-type-toggle"
            data-type={type}
            onClick={() => toggleType(type)}
          >
            <i style={{ background: colorFor(type), width: 9, height: 9, borderRadius: "50%", display: "inline-block", marginRight: 6 }} />
            {type} ({result.graph.stats.nodesByType[type]})
          </button>
        ))}
      </div>

      {truncated > 0 && (
        <div className="alert info small" style={{ marginTop: 10 }} data-testid="graph-truncated">
          Showing the first {MAX_RENDERED} nodes; {truncated} more are hidden. Toggle node types
          above to narrow the view.
        </div>
      )}

      <div className="graph-wrap" style={{ marginTop: 10, overflow: "auto", maxHeight: 560 }}>
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Floorplan knowledge graph"
          data-testid="graph-svg"
        >
          <g stroke="var(--border)" strokeWidth="1" opacity="0.55">
            {edges.map((edge) => {
              const a = positions.get(edge.source);
              const b = positions.get(edge.target);
              if (!a || !b) return null;
              return <line key={edge.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y} />;
            })}
          </g>
          <g>
            {nodes.map((node) => {
              const p = positions.get(node.id);
              if (!p) return null;
              const isSelected = selected?.id === node.id;
              return (
                <g key={node.id} data-testid="graph-node" data-node-id={node.id}>
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={isSelected ? 8 : 5}
                    fill={colorFor(node.type)}
                    stroke={isSelected ? "var(--text)" : "none"}
                    strokeWidth="2"
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelected(node)}
                  >
                    <title>{`${node.type}: ${node.label}`}</title>
                  </circle>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {selected && (
        <div className="panel" style={{ marginTop: 12 }} data-testid="graph-node-detail">
          <div className="spread">
            <h2 style={{ margin: 0 }}>
              {selected.type} — {selected.label}
            </h2>
            <button className="secondary" data-testid="graph-node-close" onClick={() => setSelected(null)}>
              Close
            </button>
          </div>
          <p className="mono small" style={{ marginBottom: 6 }}>{selected.id}</p>
          {selected.provenance && (
            <p className="small" data-testid="graph-node-provenance">
              <strong>Provenance:</strong> extractor <code>{selected.provenance.extractor}</code>
              {selected.provenance.page != null && <> · sheet {selected.provenance.page}</>}
              {selected.provenance.bbox && (
                <> · bbox [{selected.provenance.bbox.map((v) => v.toFixed(0)).join(", ")}]</>
              )}
              {selected.provenance.sourceText && (
                <> · source text “{selected.provenance.sourceText}”</>
              )}
            </p>
          )}
          <table>
            <tbody>
              {Object.entries(selected.properties).map(([key, value]) => (
                <tr key={key}>
                  <td className="muted small" style={{ width: 200 }}>{key}</td>
                  <td className="mono small">{JSON.stringify(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
