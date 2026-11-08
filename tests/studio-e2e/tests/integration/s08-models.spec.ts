import { expect, test } from "@playwright/test";
import { gotoStudio, openSection } from "../helpers";
import { ao, aoAsk, aoNodes, blockedUnlessAo } from "./ao";
import { MODEL, TOKENS, vg } from "./vg";

// S8 — models. 8.1-8.4 prove each AO role by behaviour; 8.8 is the VG model.

test.describe("S8 models", () => {
  test("8.1 EMBED + 8.2 RERANK: semantic compilation is ready", async () => {
    await blockedUnlessAo();
    const r = await (await ao()).get("/api/semantic-compilation/status");
    expect(r.status()).toBe(200);
    expect(JSON.stringify(await r.json())).toMatch(/ready|complete|succeeded/i);
  });

  test("8.4 NON_REASONING: intent, extraction and SQL validation steps run", async () => {
    await blockedUnlessAo(process.env.AO_SRC_POSTGRESQL ? null : "AO_SRC_POSTGRESQL unset");
    const ev = await aoAsk(await ao(), "What was revenue for Probe Widget PG in Pennsylvania in June 2015?");
    const nodes = aoNodes(ev);
    for (const n of ["question_intent", "question_extraction", "validate_sql_query"]) expect(nodes).toContain(n);
  });

  test("8.5/8.6 role override and broken key", async () => {
    await blockedUnlessAo("requires restarting AO with alternate NON_REASONING_* / invalid REASONING_API_KEY");
  });

  test("8.8 VeritasGraph model is listed and selectable in Studio", async ({ page }) => {
    const r = await (await vg("viewer")).get("/models/");
    expect(r.status()).toBe(200);
    expect(JSON.stringify(await r.json())).toContain(MODEL);
    await page.addInitScript((t) => sessionStorage.setItem("veritasgraph_studio_token", t), TOKENS.viewer);
    await gotoStudio(page);
    await openSection(page, "Knowledge Graph", "graphrag");
    await expect(page.locator(`#graphModel option[value="${MODEL}"]`)).toHaveCount(1);
  });
});
