"use client";

import { useState } from "react";
import type { ExtractionResult, Schedule } from "@/lib/types";

function displayColumns(schedule: Schedule): string[] {
  const derived = Array.from(
    new Set(schedule.rows.flatMap((r) => Object.keys(r).filter((k) => k.startsWith("_")))),
  ).sort();
  return [...schedule.columns.filter((c) => !c.startsWith("_")), ...derived];
}

function headerLabel(column: string): string {
  return column.startsWith("_") ? column.slice(1) : column;
}

export default function SchedulesPanel({
  result,
  onExport,
  exporting,
}: {
  result: ExtractionResult;
  onExport: (target: string, format: "csv" | "xlsx", filename: string) => void;
  exporting: boolean;
}) {
  const [open, setOpen] = useState<string | null>(result.schedules[0]?.id ?? null);

  if (result.schedules.length === 0) {
    return (
      <div data-testid="schedules-empty" className="alert info">
        No schedule tables were detected on this document. Schedules are found from ruled table
        lines, so plan-only sheets and scanned drawings will report none.
      </div>
    );
  }

  return (
    <div data-testid="schedules-panel">
      <div className="spread" style={{ marginBottom: 12 }}>
        <span className="small muted" data-testid="schedules-count">
          {result.schedules.length} schedule(s) ·{" "}
          {result.schedules.reduce((n, s) => n + s.rowCount, 0)} rows
        </span>
        <div className="row">
          <button
            className="secondary"
            data-testid="export-all-schedules-csv"
            disabled={exporting}
            onClick={() => onExport("schedules", "csv", `${result.metadata.originalFilename}-schedules`)}
          >
            Export all schedules (CSV)
          </button>
          <button
            data-testid="export-workbook-xlsx"
            disabled={exporting}
            onClick={() => onExport("all", "xlsx", `${result.metadata.originalFilename}-workbook`)}
          >
            Export workbook (Excel)
          </button>
        </div>
      </div>

      {result.schedules.map((schedule) => {
        const columns = displayColumns(schedule);
        const isOpen = open === schedule.id;
        return (
          <div className="panel" key={schedule.id} data-testid="schedule-block" data-schedule-id={schedule.id}>
            <div className="spread">
              <button
                className="secondary"
                aria-expanded={isOpen}
                data-testid="schedule-toggle"
                onClick={() => setOpen(isOpen ? null : schedule.id)}
              >
                {isOpen ? "▾" : "▸"} {schedule.title} — sheet {schedule.page} · {schedule.rowCount} rows
              </button>
              <button
                className="secondary"
                data-testid="export-schedule-csv"
                disabled={exporting}
                onClick={() =>
                  onExport(`schedule:${schedule.id}`, "csv", `${schedule.title.replace(/\s+/g, "-")}`)
                }
              >
                Export CSV
              </button>
            </div>

            {schedule.warnings.length > 0 && (
              <div className="alert info small" style={{ marginTop: 10 }} data-testid="schedule-warnings">
                {schedule.warnings.length} row(s) did not match the expected column layout and were
                exported verbatim.
              </div>
            )}

            {isOpen && (
              <div className="scroll" style={{ marginTop: 12 }}>
                <table data-testid="schedule-table">
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <th key={column} className={column.startsWith("_") ? "num" : undefined}>
                          {headerLabel(column)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.rows.map((row, i) => (
                      <tr key={i} data-testid="schedule-row">
                        {columns.map((column) => (
                          <td key={column} className={column.startsWith("_") ? "num mono" : undefined}>
                            {row[column] ?? "—"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
