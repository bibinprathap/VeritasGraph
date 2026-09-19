"use client";

import { useMemo, useState } from "react";
import type { TakeoffLine } from "@/lib/types";

const UNITS = ["EA", "SF", "LF", "CY", "HR", "LS"];

function blankLine(index: number): TakeoffLine {
  return {
    id: `to:manual:${Date.now()}:${index}`,
    csiSection: "01 00 00",
    category: "Manual",
    description: "",
    quantity: 0,
    unit: "EA",
    basis: "entered by estimator",
    confidence: "high",
    sourceNodeIds: [],
    sourcePages: [],
    origin: "manual",
  };
}

export default function TakeoffPanel({
  lines,
  onChange,
  onReset,
  onExport,
  exporting,
  assumptions,
  onAssumptionChange,
}: {
  lines: TakeoffLine[];
  onChange: (lines: TakeoffLine[]) => void;
  onReset: () => void;
  onExport: (target: string, format: "csv" | "xlsx", filename: string) => void;
  exporting: boolean;
  assumptions: Record<string, number>;
  onAssumptionChange: (ceilingHeightFeet: number) => void;
}) {
  const [category, setCategory] = useState("all");
  const [ceiling, setCeiling] = useState(String(assumptions.ceilingHeightFeet ?? 8));

  const categories = useMemo(
    () => Array.from(new Set(lines.map((l) => l.category))).sort(),
    [lines],
  );

  const visible = useMemo(
    () => (category === "all" ? lines : lines.filter((l) => l.category === category)),
    [lines, category],
  );

  const totals = useMemo(() => {
    const byUnit: Record<string, number> = {};
    for (const line of visible) {
      byUnit[line.unit] = (byUnit[line.unit] ?? 0) + line.quantity;
    }
    return byUnit;
  }, [visible]);

  function update(id: string, patch: Partial<TakeoffLine>) {
    onChange(
      lines.map((line) =>
        line.id === id
          ? { ...line, ...patch, origin: line.origin === "manual" ? "manual" : "edited" }
          : line,
      ),
    );
  }

  return (
    <div data-testid="takeoff-panel">
      <div className="spread" style={{ marginBottom: 12 }}>
        <div className="row">
          <div className="field">
            <label htmlFor="takeoff-category">Category</label>
            <select
              id="takeoff-category"
              data-testid="takeoff-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="all">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="ceiling-height">Assumed ceiling height (ft)</label>
            <input
              id="ceiling-height"
              type="number"
              step="0.5"
              min="6"
              max="20"
              data-testid="ceiling-height"
              value={ceiling}
              onChange={(e) => setCeiling(e.target.value)}
            />
          </div>
          <button
            className="secondary"
            data-testid="recalculate"
            onClick={() => onAssumptionChange(Number(ceiling))}
          >
            Recalculate
          </button>
        </div>
        <div className="row">
          <button
            className="secondary"
            data-testid="add-manual-line"
            onClick={() => onChange([blankLine(lines.length), ...lines])}
          >
            + Add manual line
          </button>
          <button className="secondary" data-testid="reset-takeoff" onClick={onReset}>
            Reset to extracted
          </button>
          <button
            className="secondary"
            data-testid="export-takeoff-csv"
            disabled={exporting}
            onClick={() => onExport("takeoff", "csv", "floorplan-takeoff")}
          >
            Export CSV
          </button>
          <button
            data-testid="export-takeoff-xlsx"
            disabled={exporting}
            onClick={() => onExport("all", "xlsx", "floorplan-takeoff")}
          >
            Export Excel
          </button>
        </div>
      </div>

      <div className="alert info small" data-testid="takeoff-totals">
        {visible.length} line(s) shown ·{" "}
        {Object.entries(totals)
          .map(([unit, value]) => `${value.toFixed(2)} ${unit}`)
          .join(" · ") || "no quantities"}
      </div>

      <div className="scroll">
        <table data-testid="takeoff-table">
          <thead>
            <tr>
              <th>CSI</th>
              <th>Category</th>
              <th>Description</th>
              <th className="num">Qty</th>
              <th>Unit</th>
              <th>Basis</th>
              <th>Confidence</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visible.map((line) => (
              <tr key={line.id} data-testid="takeoff-row" data-line-id={line.id} data-origin={line.origin}>
                <td className="mono small">{line.csiSection}</td>
                <td className="small">{line.category}</td>
                <td>
                  <input
                    type="text"
                    aria-label={`Description for ${line.id}`}
                    data-testid="takeoff-description"
                    style={{ width: "100%", minWidth: 220 }}
                    value={line.description}
                    onChange={(e) => update(line.id, { description: e.target.value })}
                  />
                </td>
                <td className="num">
                  <input
                    type="number"
                    step="0.01"
                    aria-label={`Quantity for ${line.id}`}
                    data-testid="takeoff-quantity"
                    style={{ width: 96, textAlign: "right", minWidth: 0 }}
                    value={line.quantity}
                    onChange={(e) => update(line.id, { quantity: Number(e.target.value) || 0 })}
                  />
                </td>
                <td>
                  <select
                    aria-label={`Unit for ${line.id}`}
                    data-testid="takeoff-unit"
                    style={{ minWidth: 72 }}
                    value={line.unit}
                    onChange={(e) => update(line.id, { unit: e.target.value })}
                  >
                    {UNITS.map((u) => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </td>
                <td className="small muted" data-testid="takeoff-basis">{line.basis}</td>
                <td>
                  <span className={`pill ${line.confidence}`} data-testid="takeoff-confidence">
                    {line.confidence}
                  </span>
                  {line.origin !== "auto" && (
                    <>
                      {" "}
                      <span className="pill manual" data-testid="takeoff-origin">{line.origin}</span>
                    </>
                  )}
                </td>
                <td>
                  <button
                    className="danger"
                    data-testid="takeoff-delete"
                    aria-label={`Delete ${line.id}`}
                    onClick={() => onChange(lines.filter((l) => l.id !== line.id))}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
