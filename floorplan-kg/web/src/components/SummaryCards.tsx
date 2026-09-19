"use client";

import type { ExtractionResult } from "@/lib/types";

const CARDS: Array<{ key: string; label: string; pick: (r: ExtractionResult) => number }> = [
  { key: "pages", label: "Sheets", pick: (r) => r.summary.totalPages },
  { key: "rooms", label: "Rooms", pick: (r) => r.summary.rooms },
  { key: "area", label: "Measured Area (SF)", pick: (r) => r.summary.measuredAreaSqFt },
  { key: "dimensions", label: "Dimensions", pick: (r) => r.summary.dimensions },
  { key: "openings", label: "Window Tags", pick: (r) => r.summary.openings },
  { key: "fixtures", label: "Fixtures", pick: (r) => r.summary.fixtures },
  { key: "schedules", label: "Schedules", pick: (r) => r.summary.schedules },
  { key: "nodes", label: "Graph Nodes", pick: (r) => r.summary.nodeCount },
  { key: "edges", label: "Graph Edges", pick: (r) => r.summary.edgeCount },
  { key: "takeoff", label: "Takeoff Lines", pick: (r) => r.summary.takeoffLines },
];

export default function SummaryCards({ result }: { result: ExtractionResult }) {
  return (
    <div className="cards" data-testid="summary-cards">
      {CARDS.map((card) => (
        <div className="card" key={card.key} data-testid={`card-${card.key}`}>
          <div className="k">{card.label}</div>
          <div className="v" data-testid={`card-${card.key}-value`}>
            {card.pick(result).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}
