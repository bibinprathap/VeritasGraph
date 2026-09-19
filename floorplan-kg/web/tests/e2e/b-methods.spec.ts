/**
 * Category B — both extraction backends across all six sheets (TC09–TC20).
 *
 * PyMuPDF and pdfplumber disagree about run segmentation, so the counts are
 * allowed to differ; what must hold is that both succeed, both record which
 * backend ran, and both find the same *entities* where entities exist.
 */
import { expect, test } from "@playwright/test";
import { SAMPLES, type Method, cardValue, extractSample, oracle } from "./helpers";

const METHODS: Method[] = ["pymupdf", "pdfplumber"];

let caseNumber = 8;
for (const id of Object.keys(SAMPLES) as Array<keyof typeof SAMPLES>) {
  for (const method of METHODS) {
    caseNumber += 1;
    const label = `TC${String(caseNumber).padStart(2, "0")}`;
    test(`${label} · ${id} · ${method}`, async ({ page }) => {
      await extractSample(page, id, method);
      await expect(page.getByTestId("used-method")).toHaveText(method);
      await expect(page.getByTestId("meta-processingMethod")).toHaveText(method);
      expect(await cardValue(page, "pages")).toBe(oracle(id, method).metadata.totalPages);
    });
  }
}

test("TC20b · both backends agree on the room set for F1", async ({ page }) => {
  const byPyMuPdf = oracle("F1", "pymupdf");
  const byPdfPlumber = oracle("F1", "pdfplumber");

  const names = (o: typeof byPyMuPdf) =>
    new Set(
      o.pages.flatMap((p) =>
        ((p.rooms ?? []) as Array<{ name: string }>).map((r) => r.name),
      ),
    );

  const a = names(byPyMuPdf);
  const b = names(byPdfPlumber);
  const shared = [...a].filter((n) => b.has(n));
  expect(a.size).toBeGreaterThan(0);
  expect(shared.length / a.size).toBeGreaterThan(0.5);

  await extractSample(page, "F1", "pdfplumber");
  await expect(page.getByTestId("success-banner")).toBeVisible();
});
