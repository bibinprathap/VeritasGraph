"use client";

import { GraphData } from "../lib/api";

const COLORS: Record<string, string> = {
  Patient: "#12b3a6",
  Encounter: "#7fb2ff",
  Condition: "#f5b942",
  Medication: "#c39bff",
  LabResult: "#45c17a",
  Procedure: "#ff9d6b",
  Concept: "#5a6b8c",
  Span: "#3a4a6b",
};

// Column index per node type for a simple layered layout.
const COLUMN: Record<string, number> = {
  Patient: 0,
  Encounter: 1,
  Condition: 1,
  Medication: 1,
  LabResult: 1,
  Procedure: 1,
  Concept: 2,
  Span: 3,
};

export default function GraphView({ data }: { data: GraphData }) {
  if (!data.nodes.length) {
    return <p className="muted">No graph yet. Load samples or ingest a note.</p>;
  }

  const colX = [80, 340, 620, 860];
  const rowGap = 46;
  const colCounts: Record<number, number> = {};
  const pos: Record<string, { x: number; y: number; ntype: string; label: string }> =
    {};

  for (const n of data.nodes) {
    const c = COLUMN[n.data.ntype] ?? 3;
    const idx = colCounts[c] ?? 0;
    colCounts[c] = idx + 1;
    pos[n.data.id] = {
      x: colX[c],
      y: 60 + idx * rowGap,
      ntype: n.data.ntype,
      label: n.data.label,
    };
  }

  const height =
    Math.max(...Object.values(colCounts).map((c) => 60 + c * rowGap), 300) + 40;
  const width = 1040;

  return (
    <div className="svgwrap">
      <svg width={width} height={height} style={{ display: "block" }}>
        {data.edges.map((e, i) => {
          const s = pos[e.data.source];
          const t = pos[e.data.target];
          if (!s || !t) return null;
          return (
            <line
              key={i}
              x1={s.x + 70}
              y1={s.y}
              x2={t.x - 70}
              y2={t.y}
              stroke="#2a3a5a"
              strokeWidth={1}
            />
          );
        })}
        {Object.entries(pos).map(([id, p]) => (
          <g key={id}>
            <rect
              x={p.x - 72}
              y={p.y - 14}
              width={144}
              height={28}
              rx={7}
              fill="#18243d"
              stroke={COLORS[p.ntype] ?? "#3a4a6b"}
              strokeWidth={1.5}
            />
            <circle cx={p.x - 60} cy={p.y} r={4} fill={COLORS[p.ntype] ?? "#3a4a6b"} />
            <text
              x={p.x - 50}
              y={p.y + 4}
              fill="#e6edf7"
              fontSize={11}
              fontFamily="ui-monospace, monospace"
            >
              {p.label.length > 16 ? p.label.slice(0, 15) + "…" : p.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
