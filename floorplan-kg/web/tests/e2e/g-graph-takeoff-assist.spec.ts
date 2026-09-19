/**
 * Category G — the surface that has no counterpart in the original plan:
 * the knowledge graph, manual takeoff editing, and the optional VeritasGraph
 * bridge (TC51–TC60).
 */
import { expect, test } from "@playwright/test";
import { cardValue, extractSample, oracle, openTab } from "./helpers";

test("TC51 · the graph renders nodes and exposes a legend per node type", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "graph");

  await expect(page.getByTestId("graph-svg")).toBeVisible();
  const types = Object.keys(
    (oracle("F1").graph.stats as { nodesByType: Record<string, number> }).nodesByType,
  );
  await expect(page.getByTestId("graph-type-toggle")).toHaveCount(types.length);
  expect(await page.getByTestId("graph-node").count()).toBeGreaterThan(0);
});

test("TC52 · hiding a node type removes those nodes from the canvas", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "graph");

  const before = await page.getByTestId("graph-node").count();
  const toggle = page.locator('[data-testid="graph-type-toggle"][data-type="Room"]');
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");

  const after = await page.getByTestId("graph-node").count();
  const roomCount = (oracle("F1").graph.stats as { nodesByType: Record<string, number> })
    .nodesByType.Room;
  expect(before - after).toBe(roomCount);
});

test("TC53 · clicking a node reveals its provenance back to the sheet", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "graph");

  await page.locator('[data-testid="graph-node"] circle').first().click();
  const detail = page.getByTestId("graph-node-detail");
  await expect(detail).toBeVisible();
  await expect(page.getByTestId("graph-node-provenance")).toContainText("extractor");

  await page.getByTestId("graph-node-close").click();
  await expect(detail).toHaveCount(0);
});

test("TC54 · room adjacency edges exist and connect two rooms", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "graph");

  const graph = oracle("F1").graph as {
    nodes: Array<{ id: string; type: string }>;
    edges: Array<{ source: string; target: string; type: string }>;
  };
  const rooms = new Set(graph.nodes.filter((n) => n.type === "Room").map((n) => n.id));
  const adjacency = graph.edges.filter((e) => e.type === "ADJACENT_TO");

  expect(adjacency.length).toBeGreaterThan(0);
  for (const edge of adjacency) {
    expect(rooms.has(edge.source) && rooms.has(edge.target)).toBe(true);
  }
});

test("TC55 · a manual line is added, marked as manual, and can be deleted", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "takeoff");

  const original = await page.getByTestId("takeoff-row").count();
  await page.getByTestId("add-manual-line").click();
  await expect(page.getByTestId("takeoff-row")).toHaveCount(original + 1);

  const added = page.getByTestId("takeoff-row").first();
  await expect(added).toHaveAttribute("data-origin", "manual");
  await added.getByTestId("takeoff-delete").click();
  await expect(page.getByTestId("takeoff-row")).toHaveCount(original);
});

test("TC56 · editing an auto line marks it edited, and reset restores it", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "takeoff");

  const row = page.getByTestId("takeoff-row").first();
  const lineId = await row.getAttribute("data-line-id");
  const originalQuantity = await row.getByTestId("takeoff-quantity").inputValue();

  await row.getByTestId("takeoff-quantity").fill("999");
  const edited = page.locator(`[data-line-id="${lineId}"]`);
  await expect(edited).toHaveAttribute("data-origin", "edited");

  await page.getByTestId("reset-takeoff").click();
  await expect(page.locator(`[data-line-id="${lineId}"]`)).toHaveAttribute("data-origin", "auto");
  await expect(
    page.locator(`[data-line-id="${lineId}"] [data-testid="takeoff-quantity"]`),
  ).toHaveValue(originalQuantity);
});

test("TC57 · filtering by category narrows the takeoff and updates the totals", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "takeoff");

  const all = await page.getByTestId("takeoff-row").count();
  await page.getByTestId("takeoff-category").selectOption("Flooring");

  const flooring = (oracle("F1").takeoff.lines as Array<{ category: string }>).filter(
    (l) => l.category === "Flooring",
  ).length;
  await expect(page.getByTestId("takeoff-row")).toHaveCount(flooring);
  expect(flooring).toBeLessThan(all);
  await expect(page.getByTestId("takeoff-totals")).toContainText(`${flooring} line(s) shown`);
});

test("TC58 · changing the ceiling-height assumption re-derives wall quantities", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "takeoff");
  await page.getByTestId("takeoff-category").selectOption("Gypsum Board");

  const row = page.getByTestId("takeoff-row").first();
  const lineId = await row.getAttribute("data-line-id");
  const at8ft = Number(await row.getByTestId("takeoff-quantity").inputValue());

  await page.getByTestId("ceiling-height").fill("10");
  await page.getByTestId("recalculate").click();

  // The success banner is already on screen from the first run, so wait on the
  // quantity itself rather than on a banner that never goes away.
  const quantity = page.locator(`[data-line-id="${lineId}"] [data-testid="takeoff-quantity"]`);
  await expect(quantity).not.toHaveValue(String(at8ft), { timeout: 110_000 });
  const at10ft = Number(await quantity.inputValue());
  expect(at10ft).toBeCloseTo((at8ft / 8) * 10, 1);
});

test("TC59 · door quantities come from the schedule and carry high confidence", async ({ page }) => {
  await extractSample(page, "F5");
  await openTab(page, "takeoff");
  await page.getByTestId("takeoff-category").selectOption("Doors");

  const doorLines = (oracle("F5").takeoff.lines as Array<{
    category: string; quantity: number; confidence: string;
  }>).filter((l) => l.category === "Doors");

  await expect(page.getByTestId("takeoff-row")).toHaveCount(doorLines.length);
  for (const row of await page.getByTestId("takeoff-row").all()) {
    await expect(row.getByTestId("takeoff-confidence")).toHaveText("high");
    await expect(row.getByTestId("takeoff-basis")).toContainText("door schedule marks");
  }

  // The schedule lists 18 marks; the grouped lines must still total 18.
  const total = doorLines.reduce((sum, l) => sum + l.quantity, 0);
  expect(total).toBe(18);

  // The summary cards live on the overview tab.
  await openTab(page, "overview");
  expect(await cardValue(page, "schedules")).toBeGreaterThan(0);
});

test("TC60 · the VeritasGraph panel states its availability and never blocks the app", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "assist");

  const status = page.getByTestId("assist-status");
  await expect(status).toBeVisible();
  // The availability probe is async; wait for it to settle before branching.
  await expect(status).not.toContainText("Checking for a local VeritasGraph engine");

  const available = (await status.getAttribute("data-available")) === "true";
  if (available) {
    await expect(status).toContainText("VeritasGraph engine detected");
    await expect(page.getByTestId("assist-push")).toBeEnabled();
  } else {
    await expect(status).toContainText("AI assist unavailable");
    await expect(page.getByTestId("assist-push")).toBeDisabled();
    await expect(page.getByTestId("assist-ask")).toBeDisabled();
  }

  // Either way the deterministic surface is untouched.
  await openTab(page, "takeoff");
  await expect(page.getByTestId("takeoff-table")).toBeVisible();
});
