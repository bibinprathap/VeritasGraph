import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, type Page } from "@playwright/test";

export const WEB_ROOT = path.resolve(__dirname, "..", "..");
export const PROJECT_ROOT = path.resolve(WEB_ROOT, "..");
export const PYTHON =
  process.env.FLOORPLAN_PYTHON ?? path.resolve(PROJECT_ROOT, "..", ".venv", "bin", "python");
export const SAMPLE_DIR =
  process.env.FLOORPLAN_SAMPLES ??
  path.resolve(PROJECT_ROOT, "..", "Floorplan-Dimractor", "data", "input");
export const FIXTURES = path.join(WEB_ROOT, "tests", "e2e", "fixtures");

export type Method = "pymupdf" | "pdfplumber";

/** The six sample sheets the suite exercises, keyed as in the test plan. */
export const SAMPLES = {
  F1: "Floorplan_20250928_001404.pdf",
  F2: "Floorplan_20250928_001406.pdf",
  F3: "Floorplan_20250928_174654.pdf",
  F4: "Floorplan_20250928_174714.pdf",
  F5: "House-Floor-Plans_20250928_001528.pdf",
  F6: "House-Floor-Plans_20250928_001533.pdf",
} as const;

export type SampleId = keyof typeof SAMPLES;

export type Oracle = {
  metadata: Record<string, unknown> & { processingMethod: Method; totalPages: number };
  summary: Record<string, number>;
  pages: Array<Record<string, unknown>>;
  schedules: Array<Record<string, unknown>>;
  graph: { nodes: unknown[]; edges: unknown[]; stats: Record<string, unknown> };
  takeoff: { lines: Array<Record<string, unknown>>; assumptions: Record<string, number> };
};

const oracleCache = new Map<string, Oracle>();

/**
 * Ground truth for data assertions: the engine's own output, computed out of
 * band. Comparing the rendered UI against this rather than against hard-coded
 * numbers keeps the assertions meaningful when a sample PDF changes, while
 * still catching any UI that drops or mangles what the engine produced.
 */
export function oracle(sample: SampleId | string, method: Method = "pymupdf"): Oracle {
  const filename = (SAMPLES as Record<string, string>)[sample] ?? sample;
  const key = `${filename}::${method}`;
  const cached = oracleCache.get(key);
  if (cached) return cached;

  const stdout = execFileSync(
    PYTHON,
    ["-m", "engine.cli", path.join(SAMPLE_DIR, filename), "--method", method, "--format", "json"],
    { cwd: PROJECT_ROOT, maxBuffer: 256 * 1024 * 1024, encoding: "utf8",
      env: { ...process.env, PYTHONWARNINGS: "ignore" } },
  );
  const parsed = JSON.parse(stdout) as Oracle;
  oracleCache.set(key, parsed);
  return parsed;
}

export async function gotoApp(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("app-title")).toBeVisible();
}

export async function chooseMethod(page: Page, method: Method) {
  await page.getByTestId(`method-${method}`).check();
}

export async function selectSample(page: Page, sample: SampleId | string) {
  const filename = (SAMPLES as Record<string, string>)[sample] ?? sample;
  await page.getByTestId("sample-select").selectOption({ value: filename });
  await expect(page.getByTestId("selected-input")).toContainText(filename);
}

export async function uploadFixture(page: Page, filename: string) {
  await page.getByTestId("file-input").setInputFiles(path.join(FIXTURES, filename));
}

/** Click extract and wait for either the success banner or the error banner. */
export async function runExtraction(page: Page) {
  await page.getByTestId("run-extraction").click();
  await expect(
    page.getByTestId("success-banner").or(page.getByTestId("error-banner")),
  ).toBeVisible({ timeout: 110_000 });
}

export async function extractSample(
  page: Page,
  sample: SampleId | string,
  method: Method = "pymupdf",
) {
  await gotoApp(page);
  await selectSample(page, sample);
  await chooseMethod(page, method);
  await runExtraction(page);
  await expect(page.getByTestId("success-banner")).toBeVisible();
}

export async function openTab(page: Page, tab: string) {
  await page.getByTestId(`tab-${tab}`).click();
  await expect(page.getByTestId(`tab-${tab}`)).toHaveAttribute("aria-selected", "true");
}

/** Numeric text of a summary card, e.g. `card-rooms`. */
export async function cardValue(page: Page, key: string): Promise<number> {
  const text = await page.getByTestId(`card-${key}-value`).innerText();
  return Number(text.replace(/,/g, ""));
}
