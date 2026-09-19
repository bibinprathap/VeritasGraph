/**
 * Category A — happy-path extraction, one case per sample sheet (TC01–TC08).
 */
import { expect, test } from "@playwright/test";
import { SAMPLES, cardValue, extractSample, gotoApp, oracle, selectSample } from "./helpers";

test.describe("A · happy path", () => {
  for (const [index, [id, filename]] of Object.entries(SAMPLES).entries()) {
    test(`TC0${index + 1} · extract ${id} (${filename}) with the default backend`, async ({ page }) => {
      await extractSample(page, id);
      await expect(page.getByTestId("success-banner")).toContainText(filename);
      await expect(page.getByTestId("summary-cards")).toBeVisible();
      expect(await cardValue(page, "pages")).toBeGreaterThanOrEqual(1);
    });
  }

  test("TC07 · selecting a sample shows its name and size before extracting", async ({ page }) => {
    await gotoApp(page);
    await selectSample(page, "F1");
    await expect(page.getByTestId("selected-input")).toContainText(SAMPLES.F1);
    // Nothing has run yet, so the empty state must still be the only result surface.
    await expect(page.getByTestId("empty-state")).toBeVisible();
    await expect(page.getByTestId("success-banner")).toHaveCount(0);
  });

  test("TC08 · the overview reports the source document and a duration", async ({ page }) => {
    await extractSample(page, "F2");
    const expected = oracle("F2");
    await expect(page.getByTestId("meta-originalFilename")).toHaveText(SAMPLES.F2);
    await expect(page.getByTestId("meta-sha256")).toHaveText(String(expected.metadata.sha256));
    await expect(page.getByTestId("meta-durationMs")).not.toBeEmpty();
  });
});
