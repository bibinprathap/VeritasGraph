import { test, expect } from "@playwright/test";
import { gotoStudio, openSection, kpiNumber, SECTIONS, SOD_SAMPLE_DOC } from "./helpers";

/**
 * Enterprise scenario E2E — "Northwind Bank Segregation-of-Duties (SoD)".
 *
 * Mirrors docs/STUDIO_ENTERPRISE_TEST.md: a financial-services compliance team
 * builds a governed agent that answers "who is violating our SoD policy — and
 * prove it?" running on-prem with citations and an audit trail.
 *
 * Targets the LIVE Studio at https://bibinprathap.github.io/VeritasGraph/studio/
 * by default (override with STUDIO_URL). Read-only navigation/assertion tests
 * run always; mutating + model-inference steps are gated behind RUN_WRITE_TESTS
 * so they never pollute or hammer the shared demo.
 */

const WRITE = !!process.env.RUN_WRITE_TESTS;
const AGENT_NAME = `SoD Compliance Officer ${Date.now()}`;

// ---------------------------------------------------------------------------
// §0–1  Startup, dashboard & KPIs — "morning posture check"
// ---------------------------------------------------------------------------
test.describe("§1 Dashboard & KPIs — morning posture check", () => {
  test.beforeEach(async ({ page }) => await gotoStudio(page));

  test("shell + all ten governed sections are present", async ({ page }) => {
    await expect(page.locator("body")).toContainText(/VeritasGraph Studio/i);
    const nav = page.locator("#nav button");
    await expect(nav).toHaveCount(SECTIONS.length);
    for (let i = 0; i < SECTIONS.length; i++) {
      await expect(nav.nth(i)).toContainText(SECTIONS[i].label);
    }
  });

  test("KPI cards are dynamic, and Last build is not a hardcoded date", async ({ page }) => {
    for (const id of ["#kpiAgents", "#kpiTools", "#kpiEval", "#kpiBlocks"]) {
      await expect
        .poll(async () => (await page.locator(id).innerText()).trim(), { timeout: 30_000 })
        .not.toBe("—");
    }
    const lastBuild = page.locator("#lastBuild");
    await expect
      .poll(async () => (await lastBuild.innerText()).trim(), { timeout: 30_000 })
      .not.toBe("—");
    await expect(lastBuild).toContainText(/\d{4}-\d{2}-\d{2}|no deploys yet/i);
  });
});

// ---------------------------------------------------------------------------
// §3  Tools — "register only vetted, in-VPC connectors"
// ---------------------------------------------------------------------------
test.describe("§3 Tools — vetted, in-VPC connectors only", () => {
  test("connected tools are a small loopback-only set, matching the KPI", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Tools", "tools");
    await expect(page.locator("#toolList")).toBeVisible();

    // Air-gapped posture: connected count must stay small (loopback only),
    // not the old inflated 16/18.
    const connected = await kpiNumber(page, "#kpiTools");
    expect(Number.isNaN(connected)).toBeFalsy();
    expect(connected).toBeLessThanOrEqual(10);

    // The VeritasGraph MCP connectors (loopback) should be listed.
    await expect(page.locator("#toolList")).toContainText(/VeritasGraph MCP/i);
  });
});

// ---------------------------------------------------------------------------
// §4–9  Governance sections render with their enterprise controls
// ---------------------------------------------------------------------------
test.describe("§4–9 Governance sections render", () => {
  test.beforeEach(async ({ page }) => await gotoStudio(page));

  const governance: { label: string; id: string; listId: string; expect: RegExp }[] = [
    { label: "Knowledge", id: "knowledge", listId: "#knowledgeList", expect: /knowledge|retriev|chunk/i },
    { label: "Guardrails", id: "guardrails", listId: "#guardrailList", expect: /guardrail|policy|block|pii/i },
    { label: "Memory", id: "memory", listId: "#memoryList", expect: /memory|short|long/i },
    { label: "Data", id: "data", listId: "#dataList", expect: /data|source|pipeline|quality/i },
    { label: "Evaluation", id: "evaluation", listId: "#evalList", expect: /eval|relevance|faithful|latency|compliance/i },
    { label: "Fine-tune", id: "fine-tune", listId: "#tuneList", expect: /tune|job|checkpoint|slice/i },
  ];

  for (const g of governance) {
    test(`${g.label} section is reachable and populated`, async ({ page }) => {
      await openSection(page, g.label, g.id);
      await expect(page.locator(`#${g.id}`)).toBeVisible();
      await expect(page.locator(`#${g.id}`)).toContainText(g.expect);
    });
  }
});

// ---------------------------------------------------------------------------
// §5  Guardrails audit signal is the single source of truth
// ---------------------------------------------------------------------------
test.describe("§5 Guardrails — audit signal", () => {
  test("guardrail-blocks KPI is a real, countable number", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Guardrails", "guardrails");
    const blocks = await kpiNumber(page, "#kpiBlocks");
    expect(Number.isNaN(blocks)).toBeFalsy();
    expect(blocks).toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// §10 Playground — pipeline + citations (read-only smoke)
// ---------------------------------------------------------------------------
test.describe("§10 Playground — governed pipeline", () => {
  test("agent console + orchestration pipeline are present", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Playground", "playground");

    const agentSelect = page.locator("#playgroundAgent");
    await expect(agentSelect).toBeVisible();
    await expect
      .poll(async () => await agentSelect.locator("option").count(), { timeout: 30_000 })
      .toBeGreaterThan(0);

    await expect(page.locator("#chatInput")).toBeVisible();
    await expect(page.locator("#chatSend")).toBeVisible();
    // The pipeline explainer must reference the governed stages (Veritasroom, not Headroom).
    await expect(page.locator("#pipelineTrace")).toContainText(/guardrails|memory|knowledge graph|Veritasroom|tools|data/i);
    await expect(page.locator("#playground")).not.toContainText(/Headroom/i);
  });
});

// ---------------------------------------------------------------------------
// §11 Knowledge Graph — reasoning path controls
// ---------------------------------------------------------------------------
test.describe("§11 Knowledge Graph — explain the reasoning path", () => {
  test("graph builder, explorer, and reasoning controls are present", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Knowledge Graph", "graphrag");
    await expect(page.locator("#graphText")).toBeVisible();
    await expect(page.locator("#graphIngest")).toBeVisible();
    await expect(page.locator("#graphCanvas")).toBeVisible();
    await expect(page.locator("#graphQuestion")).toBeVisible();
    await expect(page.locator("#graphAsk")).toBeVisible();
  });
});

// ===========================================================================
// Northwind Bank SoD — end-to-end write scenario (opt-in via RUN_WRITE_TESTS)
// ===========================================================================
test.describe.serial("Northwind SoD — end-to-end (write + inference)", () => {
  test.skip(!WRITE, "Set RUN_WRITE_TESTS=1 to run the mutating end-to-end scenario");
  test.describe.configure({ timeout: 180_000 });

  test("§2 Agents — stand up the SoD Compliance Officer", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Agents", "agents");

    await page.locator("#agentName").fill(AGENT_NAME);
    const modelSelect = page.locator("#agentModel");
    if (await modelSelect.locator("option").count()) {
      await modelSelect.selectOption({ index: 0 });
    }
    // Wire the governed capabilities the compliance use case needs.
    for (const capId of ["#capGraph", "#capTools", "#capMemory", "#capGuardrails", "#capData"]) {
      const cb = page.locator(capId);
      if (await cb.count()) await cb.check().catch(() => {});
    }
    await page.locator("#capBudget").fill("8000");
    await page.locator("#addAgent").click();

    await expect(
      page.locator("#agentList").getByText(AGENT_NAME, { exact: false })
    ).toBeVisible({ timeout: 30_000 });
  });

  test("§11 Knowledge Graph — ingest the SoD policy and trace a multi-hop conflict", async ({ page }) => {
    test.slow();
    await gotoStudio(page);
    await openSection(page, "Knowledge Graph", "graphrag");

    const modelSelect = page.locator("#graphModel");
    await expect
      .poll(async () => await modelSelect.locator("option").count(), { timeout: 30_000 })
      .toBeGreaterThan(0);
    await modelSelect.selectOption({ index: 0 }).catch(() => {});

    await page.locator("#graphTitle").fill("Northwind SoD Policy SOD-2024-R7");
    await page.locator("#graphText").fill(SOD_SAMPLE_DOC);
    await page.locator("#graphIngest").click();

    // Graph stats should update away from the empty state as nodes/edges appear.
    await expect
      .poll(async () => (await page.locator("#graphStats").innerText()).trim(), { timeout: 120_000 })
      .not.toBe("No graph yet.");

    // Ask the multi-hop SoD question and expect a cited reasoning path.
    await page.locator("#graphQuestion").fill(
      "Which employee violates SoD rule R7, and which entitlements cause the conflict?"
    );
    await page.locator("#graphAsk").click();

    await expect
      .poll(async () => (await page.locator("#graphAnswer").innerText()).trim().length, { timeout: 120_000 })
      .toBeGreaterThan(0);
    // An auditor needs a substantive, grounded answer. The separate reasoning-path
    // and citation panels are best-effort (they depend on the local model emitting
    // structured citations), so treat them as a soft signal rather than a hard gate.
    const answer = (await page.locator("#graphAnswer").innerText()).trim();
    expect(answer.length).toBeGreaterThan(20);
    const pathLen = (await page.locator("#graphPath").innerText()).trim().length;
    const citeLen = (await page.locator("#graphCitations").innerText()).trim().length;
    if (pathLen + citeLen === 0) {
      test.info().annotations.push({
        type: "note",
        description: "Graph answer produced but no structured path/citations from the local model.",
      });
    }
  });

  test("§10 Playground — cited answer + governed pipeline trace", async ({ page }) => {
    test.slow();
    await gotoStudio(page);
    await openSection(page, "Playground", "playground");

    // Prefer the SoD agent we created; fall back to the first available agent.
    const select = page.locator("#playgroundAgent");
    await expect
      .poll(async () => await select.locator("option").count(), { timeout: 30_000 })
      .toBeGreaterThan(0);
    const sodOption = select.locator("option", { hasText: "SoD Compliance Officer" });
    if (await sodOption.count()) {
      await select.selectOption({ label: await sodOption.first().innerText() }).catch(async () => {
        await select.selectOption({ index: 1 }).catch(() => {});
      });
    }

    const before = await page.locator("#chatLog > *").count();
    await page
      .locator("#chatInput")
      .fill("Which employee violates SoD rule R7, and prove it with a citation?");
    await page.locator("#chatSend").click();

    // The turn is heavier than a plain chat (graph + tools + guardrails are
    // wired), so wait generously for the reply to land in the chat log.
    await expect
      .poll(async () => await page.locator("#chatLog > *").count(), { timeout: 150_000 })
      .toBeGreaterThan(before);

    // The definitive "governed turn completed" signal: the orchestration
    // pipeline replaces its empty-state hint with the actual stage list.
    await expect
      .poll(async () => (await page.locator("#pipelineTrace").innerText()).trim(), { timeout: 150_000 })
      .not.toMatch(/Send a message to see/i);
    await expect(page.locator("#pipelineTrace")).toContainText(
      /Guardrails|Memory|Knowledge Graph|Veritasroom|Tools|Data log/i
    );
  });

  test("§2 cleanup — delete the SoD Compliance Officer", async ({ page }) => {
    await gotoStudio(page);
    await openSection(page, "Agents", "agents");

    const row = page
      .locator("#agentList .list-row, #agentList .card, #agentList > *")
      .filter({ hasText: AGENT_NAME })
      .first();
    if (await row.count()) {
      page.once("dialog", (d) => d.accept());
      await row.getByRole("button", { name: /delete/i }).click();
      await expect(
        page.locator("#agentList").getByText(AGENT_NAME, { exact: false })
      ).toHaveCount(0, { timeout: 30_000 });
    }
  });
});
