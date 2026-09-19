/**
 * Category D — the rendered UI must match the engine oracle (TC31–TC40).
 */
import { expect, test } from "@playwright/test";
import { cardValue, extractSample, oracle, openTab } from "./helpers";

test("TC31 · room count matches the oracle", async ({ page }) => {
  await extractSample(page, "F1");
  expect(await cardValue(page, "rooms")).toBe(oracle("F1").summary.rooms);
});

test("TC32 · measured area matches the oracle", async ({ page }) => {
  await extractSample(page, "F1");
  expect(await cardValue(page, "area")).toBeCloseTo(oracle("F1").summary.measuredAreaSqFt, 0);
});

test("TC33 · page count matches the oracle for a multi-sheet set", async ({ page }) => {
  await extractSample(page, "F5");
  expect(await cardValue(page, "pages")).toBe(oracle("F5").summary.totalPages);
});

test("TC34 · dimension, fixture and window-tag counts match", async ({ page }) => {
  await extractSample(page, "F1");
  const expected = oracle("F1").summary;
  expect(await cardValue(page, "dimensions")).toBe(expected.dimensions);
  expect(await cardValue(page, "fixtures")).toBe(expected.fixtures);
  expect(await cardValue(page, "openings")).toBe(expected.openings);
});

test("TC35 · every rendered room row appears in the oracle with the same area", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "rooms");

  const expected = new Map(
    oracle("F1").pages.flatMap((p) =>
      ((p.rooms ?? []) as Array<{ id: string; name: string; areaSqFt: number | null }>).map(
        (r) => [r.id, r],
      ),
    ),
  );

  const rows = await page.getByTestId("room-row").all();
  expect(rows.length).toBe(expected.size);
  for (const row of rows) {
    const id = await row.getAttribute("data-room-id");
    const source = expected.get(id!);
    expect(source, `room ${id} is not in the oracle`).toBeTruthy();
    await expect(row.getByTestId("room-name")).toHaveText(source!.name);
    const shown = await row.getByTestId("room-area").innerText();
    if (source!.areaSqFt == null) {
      expect(shown).toBe("—");
    } else {
      expect(Number(shown)).toBeCloseTo(source!.areaSqFt, 2);
    }
  }
});

test("TC36 · dimension values are positive and feet+inches normalise correctly", async ({ page }) => {
  await extractSample(page, "F5");
  const dims = oracle("F5").pages.flatMap(
    (p) => (p.dimensions ?? []) as Array<{ raw: string; inches: number }>,
  );
  expect(dims.length).toBeGreaterThan(0);
  for (const dim of dims) {
    expect(dim.inches).toBeGreaterThan(0);
  }

  // Spot-check the notation that a naive parser gets wrong: 11'-8 3/4".
  const hyphenated = dims.filter((d) => /^\d+'-\d/.test(d.raw));
  expect(hyphenated.length).toBeGreaterThan(0);
  for (const dim of hyphenated.slice(0, 40)) {
    const m = /^(\d+)'-(\d+)(?:\s+(\d+)\/(\d+))?"?$/.exec(dim.raw);
    if (!m) continue;
    const expectedInches =
      Number(m[1]) * 12 + Number(m[2]) + (m[3] ? Number(m[3]) / Number(m[4]) : 0);
    expect(dim.inches).toBeCloseTo(expectedInches, 4);
  }
});

test("TC37 · window tags decode to real sizes", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "graph");
  const types = (oracle("F1").graph.nodes as Array<{
    type: string;
    label: string;
    properties: { widthInches?: number; heightInches?: number; operation?: string };
  }>).filter((n) => n.type === "OpeningType");

  expect(types.length).toBeGreaterThan(0);
  for (const node of types) {
    // "3040SH" means 3'-0" x 4'-0", i.e. 36" x 48" — not 30" x 40".
    const m = /^(\d)(\d)(\d)(\d)[A-Z]{2,3}$/.exec(node.label);
    expect(m, `${node.label} should be a decodable tag`).toBeTruthy();
    expect(node.properties.widthInches).toBe(Number(m![1]) * 12 + Number(m![2]));
    expect(node.properties.heightInches).toBe(Number(m![3]) * 12 + Number(m![4]));
    expect(node.properties.operation).toBeTruthy();
  }
});

test("TC38 · the door schedule renders every oracle row", async ({ page }) => {
  await extractSample(page, "F5");
  await openTab(page, "schedules");

  const doorSchedule = (oracle("F5").schedules as Array<{
    id: string; kind: string; rowCount: number; rows: Array<Record<string, unknown>>;
  }>).find((s) => s.kind === "door");
  expect(doorSchedule, "F5 should contain a door schedule").toBeTruthy();

  const block = page.locator('[data-testid="schedule-block"]', {
    has: page.locator(`text=${doorSchedule!.rowCount} rows`),
  }).first();
  await expect(block).toBeVisible();

  const table = page.locator(`[data-schedule-id="${doorSchedule!.id}"] [data-testid="schedule-table"]`);
  if ((await table.count()) === 0) {
    await page.locator(`[data-schedule-id="${doorSchedule!.id}"] [data-testid="schedule-toggle"]`).click();
  }
  await expect(
    page.locator(`[data-schedule-id="${doorSchedule!.id}"] [data-testid="schedule-row"]`),
  ).toHaveCount(doorSchedule!.rowCount);

  // Marks must be unique and contiguous — a mis-split column shows up here first.
  const marks = doorSchedule!.rows.map((r) => Number(r.Mark));
  expect(new Set(marks).size).toBe(marks.length);
  expect(Math.min(...marks)).toBe(1);
});

test("TC39 · takeoff line count and quantities match the oracle", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "takeoff");

  const expected = oracle("F1").takeoff.lines as Array<{ id: string; quantity: number }>;
  await expect(page.getByTestId("takeoff-row")).toHaveCount(expected.length);

  const byId = new Map(expected.map((l) => [l.id, l.quantity]));
  for (const row of await page.getByTestId("takeoff-row").all()) {
    const id = await row.getAttribute("data-line-id");
    const value = await row.getByTestId("takeoff-quantity").inputValue();
    expect(Number(value)).toBeCloseTo(byId.get(id!)!, 2);
  }
});

test("TC40 · graph node and edge counts match, and every node carries provenance", async ({ page }) => {
  await extractSample(page, "F5");
  await openTab(page, "graph");

  const stats = oracle("F5").graph.stats as { nodeCount: number; edgeCount: number };
  await expect(page.getByTestId("graph-stats")).toContainText(`${stats.nodeCount} nodes`);
  await expect(page.getByTestId("graph-stats")).toContainText(`${stats.edgeCount} edges`);

  const nodes = oracle("F5").graph.nodes as Array<{ id: string; provenance?: { extractor?: string } }>;
  const missing = nodes.filter((n) => !n.provenance?.extractor);
  expect(missing.map((n) => n.id)).toEqual([]);
});
