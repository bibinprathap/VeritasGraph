/**
 * Category E — malformed and degenerate inputs (TC41–TC45).
 *
 * The contract for every one of these is the same: a clear message or an
 * honestly empty result, and a page that stays usable. Never a crash, never a
 * silent wrong number.
 */
import { expect, test } from "@playwright/test";
import { FIXTURES, gotoApp, runExtraction, uploadFixture } from "./helpers";
import path from "node:path";

test("TC41 · the uploader only accepts PDFs", async ({ page }) => {
  await gotoApp(page);
  await expect(page.getByTestId("file-input")).toHaveAttribute("accept", /pdf/);

  // Bypass the accept filter the way a determined user would, and confirm the
  // server still refuses it.
  const response = await page.request.post("/api/process", {
    multipart: {
      file: { name: "sample.txt", mimeType: "text/plain", buffer: Buffer.from("not a pdf") },
      method: "pymupdf",
    },
  });
  expect(response.status()).toBe(415);
  expect((await response.json()).error).toContain("Only .pdf files");
});

test("TC42 · a corrupt PDF is handled without crashing", async ({ page }) => {
  await gotoApp(page);
  await uploadFixture(page, "corrupt.pdf");
  await runExtraction(page);

  // PyMuPDF salvages what it can; either a stated error or an honestly empty
  // result is acceptable, an unhandled crash is not.
  const failed = await page.getByTestId("error-banner").count();
  if (failed) {
    await expect(page.getByTestId("error-banner")).toContainText("Error processing PDF");
  } else {
    await expect(page.getByTestId("card-rooms-value")).toHaveText("0");
    await expect(page.getByTestId("card-takeoff-value")).toHaveText("0");
  }
  await expect(page.getByTestId("run-extraction")).toBeEnabled();
});

test("TC43 · a zero-byte PDF produces a stated error, not a stack trace", async ({ page }) => {
  await gotoApp(page);
  await uploadFixture(page, "empty.pdf");
  await runExtraction(page);

  await expect(page.getByTestId("error-banner")).toContainText("Error processing PDF");
  await expect(page.getByTestId("error-banner")).not.toContainText("Traceback");
  await expect(page.getByTestId("run-extraction")).toBeEnabled();
});

test("TC44 · an image-only sheet completes with zero text entities", async ({ page }) => {
  await gotoApp(page);
  await uploadFixture(page, "scanned.pdf");
  await runExtraction(page);

  // No OCR by design: a born-image sheet yields a page and nothing else.
  await expect(page.getByTestId("success-banner")).toBeVisible();
  await expect(page.getByTestId("card-pages-value")).toHaveText("1");
  await expect(page.getByTestId("card-rooms-value")).toHaveText("0");
  await expect(page.getByTestId("card-dimensions-value")).toHaveText("0");
  await expect(page.getByTestId("card-schedules-value")).toHaveText("0");
});

test("TC45 · the API rejects an unknown sample name and a missing body", async ({ page }) => {
  const unknown = await page.request.post("/api/process", {
    multipart: { sample: "../../etc/passwd", method: "pymupdf" },
  });
  expect(unknown.status()).toBe(404);

  const empty = await page.request.post("/api/process", { multipart: { method: "pymupdf" } });
  expect(empty.status()).toBe(400);
  expect((await empty.json()).error).toContain("Provide a PDF");

  const badExport = await page.request.post("/api/export", { data: { format: "csv" } });
  expect(badExport.status()).toBe(400);

  // And the fixture directory is where the suite thinks it is.
  expect(path.join(FIXTURES, "corrupt.pdf")).toContain("fixtures");
});
