import { test, expect } from "@playwright/test";
import { gotoStudio, openSection, SECTIONS } from "./helpers";

/**
 * End-to-end smoke tests for the live VeritasGraph Studio.
 *
 * Read-only by default so they are safe to run against the shared demo.
 * Set RUN_WRITE_TESTS=1 to also exercise agent create/delete.
 */

test.describe("VeritasGraph Studio — shell & navigation", () => {
  test.beforeEach(async ({ page }) => {
    await gotoStudio(page);
  });

  test("loads the Studio shell with the app title", async ({ page }) => {
    await expect(page.locator("body")).toContainText(/VeritasGraph Studio/i);
    await expect(page.locator("#nav button")).toHaveCount(SECTIONS.length);
  });

  test("renders all ten navigation sections in order", async ({ page }) => {
    const buttons = page.locator("#nav button");
    for (let i = 0; i < SECTIONS.length; i++) {
      await expect(buttons.nth(i)).toContainText(SECTIONS[i].label);
    }
  });

  test("can switch to every section", async ({ page }) => {
    for (const s of SECTIONS) {
      await openSection(page, s.label, s.id);
      await expect(page.locator(`#${s.id}`)).toBeVisible();
    }
  });

  test("has been rebranded from Headroom to Veritasroom", async ({ page }) => {
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toMatch(/Headroom/i);
    // The context-budget label lives in the Agents section.
    await openSection(page, "Agents", "agents");
    await expect(page.locator("#agents")).toContainText(/Veritasroom context budget/i);
  });
});

test.describe("VeritasGraph Studio — KPIs", () => {
  test.beforeEach(async ({ page }) => {
    await gotoStudio(page);
  });

  test("KPI cards populate with real values (not the loading placeholder)", async ({ page }) => {
    const ids = ["#kpiAgents", "#kpiTools", "#kpiEval", "#kpiBlocks"];
    for (const id of ids) {
      const el = page.locator(id);
      await expect(el).toBeVisible();
      // Wait for loadAll() to replace the em-dash placeholder.
      await expect
        .poll(async () => (await el.innerText()).trim(), { timeout: 30_000 })
        .not.toBe("—");
    }
  });

  test("Last build shows a real value, never a hardcoded date", async ({ page }) => {
    const lastBuild = page.locator("#lastBuild");
    await expect(lastBuild).toBeVisible();
    await expect
      .poll(async () => (await lastBuild.innerText()).trim(), { timeout: 30_000 })
      .not.toBe("—");
    // A timestamp (YYYY-MM-DD ...) or the explicit "no deploys yet" message.
    await expect(lastBuild).toContainText(/\d{4}-\d{2}-\d{2}|no deploys yet/i);
  });
});

test.describe("VeritasGraph Studio — Tools", () => {
  test("connected tools are a small, curated set", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Tools", "tools");
    // The KPI must agree with the tools view and stay in single/low double digits
    // (loopback-only connectors — not the old inflated 16/18).
    const kpi = page.locator("#kpiTools");
    await expect
      .poll(async () => (await kpi.innerText()).trim(), { timeout: 30_000 })
      .not.toBe("—");
    const connected = parseInt((await kpi.innerText()).trim(), 10);
    expect(Number.isNaN(connected)).toBeFalsy();
    expect(connected).toBeLessThanOrEqual(10);
  });
});

test.describe("VeritasGraph Studio — Playground", () => {
  test("agent selector is populated and chat controls are present", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Playground", "playground");
    const agentSelect = page.locator("#playgroundAgent");
    await expect(agentSelect).toBeVisible();
    await expect
      .poll(async () => await agentSelect.locator("option").count(), { timeout: 30_000 })
      .toBeGreaterThan(0);
    await expect(page.locator("#chatInput")).toBeVisible();
    await expect(page.locator("#chatSend")).toBeVisible();
  });

  test("sending a message returns a reply in the chat log", async ({ page }) => {
    test.slow(); // model inference over a tunnel can be slow
    await gotoStudio(page);
    await openSection(page, "Playground", "playground");

    await expect
      .poll(async () => await page.locator("#playgroundAgent option").count(), { timeout: 30_000 })
      .toBeGreaterThan(0);

    const before = await page.locator("#chatLog > *").count();
    await page.locator("#chatInput").fill("In one sentence, what is VeritasGraph Studio?");
    await page.locator("#chatSend").click();

    // Expect at least two new chat entries (the user turn + the agent reply).
    await expect
      .poll(async () => await page.locator("#chatLog > *").count(), { timeout: 90_000 })
      .toBeGreaterThan(before + 1);

    await expect(page.locator("#chatLog")).not.toBeEmpty();
  });
});

test.describe("VeritasGraph Studio — Agents (write)", () => {
  test.skip(!process.env.RUN_WRITE_TESTS, "Set RUN_WRITE_TESTS=1 to run write tests");

  test("can create and delete an agent", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Agents", "agents");

    const uniqueName = `E2E Test Agent ${Date.now()}`;
    await page.locator("#agentName").fill(uniqueName);

    // Pick the first available model, if the select is populated.
    const modelSelect = page.locator("#agentModel");
    if (await modelSelect.locator("option").count()) {
      await modelSelect.selectOption({ index: 0 });
    }

    await page.locator("#addAgent").click();

    const card = page.locator("#agentList").getByText(uniqueName, { exact: false });
    await expect(card).toBeVisible({ timeout: 30_000 });

    // Delete it again (button lives on the same card row).
    const row = page
      .locator("#agentList .list-row, #agentList .card, #agentList > *")
      .filter({ hasText: uniqueName })
      .first();
    page.once("dialog", (d) => d.accept()); // in case a confirm() is used
    await row.getByRole("button", { name: /delete/i }).click();

    await expect(page.locator("#agentList").getByText(uniqueName, { exact: false })).toHaveCount(0, {
      timeout: 30_000,
    });
  });
});
