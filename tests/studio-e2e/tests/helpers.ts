import { expect, Page } from "@playwright/test";

/** The full Studio entry URL (same value the Playwright config uses as baseURL). */
export const STUDIO_URL =
  process.env.STUDIO_URL || "https://bibinprathap.github.io/VeritasGraph/studio/";

/**
 * The ten left-nav sections of VeritasGraph Studio, in order, mapped to the
 * section container id used by setSection() in the app.
 */
export const SECTIONS: { id: string; label: string }[] = [
  { id: "agents", label: "Agents" },
  { id: "tools", label: "Tools" },
  { id: "knowledge", label: "Knowledge" },
  { id: "guardrails", label: "Guardrails" },
  { id: "memory", label: "Memory" },
  { id: "data", label: "Data" },
  { id: "evaluation", label: "Evaluation" },
  { id: "fine-tune", label: "Fine-tune" },
  { id: "playground", label: "Playground" },
  { id: "graphrag", label: "Knowledge Graph" },
];

/**
 * Navigate to the Studio, transparently following the GitHub Pages
 * meta-refresh redirect to the live tunnel, and wait until the SPA shell
 * (the left-nav) has rendered.
 */
export async function gotoStudio(page: Page): Promise<void> {
  // Navigate to the FULL entry URL (not "/", which would resolve to the origin
  // root and 404 on GitHub Pages project sites).
  await page.goto(STUDIO_URL, { waitUntil: "domcontentloaded" });

  // The GitHub Pages landing page redirects via <meta http-equiv="refresh">.
  // If the auto-redirect is slow, click the fallback link explicitly.
  const nav = page.locator("#nav button");
  try {
    await nav.first().waitFor({ state: "visible", timeout: 15_000 });
  } catch {
    const fallback = page.getByRole("link", { name: /click here if not redirected/i });
    if (await fallback.count()) {
      await fallback.first().click();
    }
    await nav.first().waitFor({ state: "visible", timeout: 45_000 });
  }

  // The app title should be present once the shell is up.
  await expect(page.locator("body")).toContainText(/VeritasGraph Studio/i);
}

/** Click a left-nav item by its visible label and confirm the section is active. */
export async function openSection(page: Page, label: string, id: string): Promise<void> {
  await page.locator(`#nav button[data-target="${id}"]`).click();
  await expect(page.locator(`#${id}`)).toHaveClass(/active/);
}

/**
 * Read a KPI card's numeric value once loadAll() has replaced the "—"
 * placeholder. Returns NaN if the value isn't numeric (e.g. a percentage cell).
 */
export async function kpiNumber(page: Page, id: string): Promise<number> {
  const el = page.locator(id);
  await expect
    .poll(async () => (await el.innerText()).trim(), { timeout: 30_000 })
    .not.toBe("—");
  const raw = (await el.innerText()).trim().replace("%", "");
  return parseFloat(raw);
}

/**
 * A small, self-contained "Segregation of Duties" document used to seed the
 * knowledge graph for the Northwind Bank enterprise scenario. It intentionally
 * encodes a multi-hop SoD conflict (one person who can both create a vendor and
 * approve payments).
 */
export const SOD_SAMPLE_DOC = [
  "Northwind Bank Segregation of Duties Policy SOD-2024-R7.",
  "Rule R7 states that no single employee may both create a vendor and approve payments.",
  "Alice has the Accounts Payable role, which grants the Approve-Payments entitlement.",
  "Alice also has the Vendor Management role, which grants the Create-Vendor entitlement.",
  "Therefore Alice holds two entitlements that conflict with SoD rule R7.",
  "Bob has only the Accounts Payable role and does not violate rule R7.",
].join(" ");

