/**
 * Category C — UI surface, controls and tab behaviour (TC21–TC30).
 */
import { expect, test } from "@playwright/test";
import { SAMPLES, extractSample, gotoApp, openTab, selectSample } from "./helpers";

test("TC21 · title and description render", async ({ page }) => {
  await gotoApp(page);
  await expect(page.getByTestId("app-title")).toContainText("Floorplan Knowledge Graph");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("TC22 · empty state is shown before any extraction", async ({ page }) => {
  await gotoApp(page);
  await expect(page.getByTestId("empty-state")).toContainText("Upload a PDF or pick a sample");
});

test("TC23 · bundled samples are listed in the picker", async ({ page }) => {
  await gotoApp(page);
  const options = page.getByTestId("sample-select").locator("option");
  await expect(options).toHaveCount(Object.keys(SAMPLES).length + 1);
  for (const filename of Object.values(SAMPLES)) {
    await expect(page.getByTestId("sample-select")).toContainText(filename);
  }
});

test("TC24 · both extraction backends are offered, PyMuPDF by default", async ({ page }) => {
  await gotoApp(page);
  await expect(page.getByTestId("method-pymupdf")).toBeChecked();
  await expect(page.getByTestId("method-pdfplumber")).not.toBeChecked();
  await page.getByTestId("method-pdfplumber").check();
  await expect(page.getByTestId("method-pdfplumber")).toBeChecked();
});

test("TC25 · no result tabs exist until an extraction has run", async ({ page }) => {
  await gotoApp(page);
  for (const tab of ["overview", "rooms", "schedules", "takeoff", "graph", "assist"]) {
    await expect(page.getByTestId(`tab-${tab}`)).toHaveCount(0);
  }
});

test("TC26 · running with no input selected reports a clear error", async ({ page }) => {
  await gotoApp(page);
  await page.getByTestId("run-extraction").click();
  await expect(page.getByTestId("error-banner")).toContainText("Choose a PDF or pick a bundled sample");
});

test("TC27 · every tab opens and renders its panel", async ({ page }) => {
  await extractSample(page, "F5");
  const panels: Record<string, string> = {
    overview: "overview-panel",
    rooms: "rooms-panel",
    schedules: "schedules-panel",
    takeoff: "takeoff-panel",
    graph: "graph-panel",
    assist: "assist-panel",
  };
  for (const [tab, panel] of Object.entries(panels)) {
    await openTab(page, tab);
    await expect(page.getByTestId(panel)).toBeVisible();
  }
});

test("TC28 · the processing banner appears while the engine runs", async ({ page }) => {
  await gotoApp(page);
  await selectSample(page, "F5");
  await page.getByTestId("run-extraction").click();
  await expect(page.getByTestId("processing-banner")).toContainText("Processing PDF");
  await expect(page.getByTestId("success-banner")).toBeVisible({ timeout: 110_000 });
  await expect(page.getByTestId("processing-banner")).toHaveCount(0);
});

test("TC29 · the rooms table can be filtered to sized rooms and re-sorted", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "rooms");

  const before = await page.getByTestId("room-row").count();
  await page.getByTestId("rooms-sized-only").check();
  const after = await page.getByTestId("room-row").count();
  expect(after).toBeLessThanOrEqual(before);
  for (const cell of await page.getByTestId("room-area").all()) {
    expect(await cell.innerText()).not.toBe("—");
  }

  await page.getByTestId("rooms-sort").selectOption("area");
  const areas = (await page.getByTestId("room-area").allInnerTexts()).map(Number);
  const sorted = [...areas].sort((a, b) => b - a);
  expect(areas).toEqual(sorted);
});

test("TC30 · selecting a file clears a previously chosen sample", async ({ page }) => {
  await gotoApp(page);
  await selectSample(page, "F1");
  await page.getByTestId("file-input").setInputFiles({
    name: "hand-picked.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n%%EOF\n"),
  });
  await expect(page.getByTestId("selected-input")).toContainText("hand-picked.pdf");
  await expect(page.getByTestId("sample-select")).toHaveValue("");
});
