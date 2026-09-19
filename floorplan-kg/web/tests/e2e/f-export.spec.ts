/**
 * Category F — CSV and Excel export (TC46–TC50).
 */
import { expect, test } from "@playwright/test";
import { promises as fs } from "node:fs";
import { extractSample, oracle, openTab } from "./helpers";

async function downloadText(page: import("@playwright/test").Page, testId: string) {
  const waiter = page.waitForEvent("download");
  await page.getByTestId(testId).first().click();
  const download = await waiter;
  const filePath = await download.path();
  return { download, text: await fs.readFile(filePath!, "utf8") };
}

test("TC46 · takeoff CSV downloads with the expected header and row count", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "takeoff");

  const { download, text } = await downloadText(page, "export-takeoff-csv");
  expect(download.suggestedFilename()).toMatch(/\.csv$/);
  const lines = text.trim().split("\r\n");
  expect(lines[0]).toBe(
    "ID,CSI Section,Category,Description,Quantity,Unit,Basis,Confidence,Origin,Sheets,Source Nodes",
  );
  expect(lines.length - 1).toBe(oracle("F1").takeoff.lines.length);
});

test("TC47 · schedule CSV contains the parsed door schedule rows", async ({ page }) => {
  await extractSample(page, "F5");
  await openTab(page, "schedules");

  const { text } = await downloadText(page, "export-all-schedules-csv");
  expect(text).toContain("# Door Schedule");
  expect(text).toContain("Mark,Type,Width,Height");
  // Marks 1..18 must all survive the export.
  for (const mark of [1, 9, 18]) {
    expect(text).toMatch(new RegExp(`\\n${mark},`));
  }
});

test("TC48 · the Excel workbook downloads as a real xlsx package", async ({ page }) => {
  await extractSample(page, "F5");
  await openTab(page, "schedules");

  const waiter = page.waitForEvent("download");
  await page.getByTestId("export-workbook-xlsx").click();
  const download = await waiter;
  expect(download.suggestedFilename()).toMatch(/\.xlsx$/);

  const buffer = await fs.readFile((await download.path())!);
  // A valid OOXML package is a zip; "PK\x03\x04" is the local file header.
  expect(buffer.subarray(0, 4)).toEqual(Buffer.from([0x50, 0x4b, 0x03, 0x04]));
  expect(buffer.toString("latin1")).toContain("xl/workbook.xml");
  expect(buffer.length).toBeGreaterThan(2000);
});

test("TC49 · a single schedule exports on its own", async ({ page }) => {
  await extractSample(page, "F5");
  await openTab(page, "schedules");

  const { text } = await downloadText(page, "export-schedule-csv");
  expect(text.split("\r\n")[0]).toContain("Mark");
  expect(text.trim().split("\r\n").length).toBeGreaterThan(2);
});

test("TC50 · manual takeoff edits are reflected in the exported CSV", async ({ page }) => {
  await extractSample(page, "F1");
  await openTab(page, "takeoff");

  await page.getByTestId("add-manual-line").click();
  const first = page.getByTestId("takeoff-row").first();
  await first.getByTestId("takeoff-description").fill("Site supervision allowance");
  await first.getByTestId("takeoff-quantity").fill("42.5");
  await first.getByTestId("takeoff-unit").selectOption("HR");

  const { text } = await downloadText(page, "export-takeoff-csv");
  expect(text).toContain("Site supervision allowance");
  expect(text).toContain("42.5,HR");
  expect(text.trim().split("\r\n").length - 1).toBe(oracle("F1").takeoff.lines.length + 1);
});
