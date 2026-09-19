"use client";

import { useMemo, useState } from "react";
import type { ExtractionResult, Room } from "@/lib/types";

type Sort = "name" | "area" | "page";

export default function RoomsTable({ result }: { result: ExtractionResult }) {
  const [sort, setSort] = useState<Sort>("page");
  const [sizedOnly, setSizedOnly] = useState(false);

  const rooms = useMemo(() => {
    const all: Room[] = result.pages.flatMap((p) => p.rooms);
    const filtered = sizedOnly ? all.filter((r) => r.areaSqFt != null) : all;
    const sorted = [...filtered];
    sorted.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "area") return (b.areaSqFt ?? -1) - (a.areaSqFt ?? -1);
      return a.page - b.page || a.name.localeCompare(b.name);
    });
    return sorted;
  }, [result, sort, sizedOnly]);

  const total = rooms.reduce((sum, r) => sum + (r.areaSqFt ?? 0), 0);

  return (
    <div data-testid="rooms-panel">
      <div className="spread" style={{ marginBottom: 10 }}>
        <div className="row">
          <div className="field">
            <label htmlFor="room-sort">Sort by</label>
            <select
              id="room-sort"
              data-testid="rooms-sort"
              value={sort}
              onChange={(e) => setSort(e.target.value as Sort)}
            >
              <option value="page">Sheet</option>
              <option value="name">Name</option>
              <option value="area">Area</option>
            </select>
          </div>
          <label className="small" style={{ display: "flex", gap: 6, alignItems: "center", paddingBottom: 8 }}>
            <input
              type="checkbox"
              data-testid="rooms-sized-only"
              checked={sizedOnly}
              onChange={(e) => setSizedOnly(e.target.checked)}
            />
            Only rooms with a measured size
          </label>
        </div>
        <div className="small muted" data-testid="rooms-total">
          {rooms.length} rooms · {total.toFixed(2)} SF
        </div>
      </div>

      {rooms.length === 0 ? (
        <p className="muted" data-testid="rooms-empty">No rooms were detected on this document.</p>
      ) : (
        <div className="scroll">
          <table data-testid="rooms-table">
            <thead>
              <tr>
                <th className="num">Sheet</th>
                <th>Room</th>
                <th>Labelled size</th>
                <th className="num">Area (SF)</th>
                <th className="num">Perimeter (LF)</th>
                <th>Fixtures</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {rooms.map((room) => (
                <tr key={room.id} data-testid="room-row" data-room-id={room.id}>
                  <td className="num">{room.page}</td>
                  <td data-testid="room-name">{room.name}</td>
                  <td className="mono">{room.sizeRaw ?? "—"}</td>
                  <td className="num" data-testid="room-area">{room.areaSqFt?.toFixed(2) ?? "—"}</td>
                  <td className="num">{room.perimeterFeet?.toFixed(2) ?? "—"}</td>
                  <td className="small">{room.fixtures.join(", ") || "—"}</td>
                  <td>
                    <span className={`pill ${room.source === "label+size" ? "high" : "low"}`}>
                      {room.source}
                    </span>
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
