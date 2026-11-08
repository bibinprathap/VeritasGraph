import { expect, test } from "@playwright/test";
import { SOD_SAMPLE_DOC, gotoStudio, openSection } from "../helpers";
import { MODEL, TOKENS, ask, graph, ingest, vg } from "./vg";

// C4, C5, C6, C7 — real Ollama answers must cite only retrieved sources,
// abstain on nothing/vague input, and count only genuinely new entities.

const IMPORTED = {
  nodes: [
    { id: "n1", name: "Zephyr Ledger", type: "system", description: "Zephyr Ledger is the general-ledger system of record used by the finance team." },
    { id: "n2", name: "Finance Team", type: "organization", description: "The finance team owns month-end close." },
  ],
  edges: [{ source: "n1", target: "n2", description: "Zephyr Ledger is operated by the Finance Team." }],
};

test.describe("S3 citations and abstention (C4-C7)", () => {
  test.beforeAll(async () => {
    expect((await (await vg("admin")).delete("/graphrag/graph")).status()).toBe(200);
    const editor = await vg("editor");
    await ingest(editor, "SoD policy", SOD_SAMPLE_DOC);
    const imp = await editor.post("/graphrag/import", {
      data: { graph: IMPORTED, format: "auto", title: "Imported finance systems" },
    });
    expect(imp.status(), await imp.text()).toBe(200);
  });

  test("3.1 every citation was retrieved; grounded matches citations (3 runs)", async () => {
    const viewer = await vg("viewer");
    for (let i = 0; i < 3; i++) {
      const res = await ask(viewer, "Who may approve vendor payments and what conflicts must be avoided?");
      const retrieved = new Set<string>(res.retrieved_source_ids ?? []);
      for (const c of res.citations ?? []) expect(retrieved, `citation ${c.id} was not retrieved`).toContain(c.id);
      if (!res.abstained) expect(res.grounded).toBe((res.citations ?? []).length > 0);
      test.info().annotations.push({
        type: `run${i + 1}`,
        description: `abstained=${res.abstained} grounded=${res.grounded} citations=${(res.citations ?? []).length} unknown=${(res.unknown_citations ?? []).length}`,
      });
    }
  });

  test("3.2 imported facts are retrievable under imp_ ids", async () => {
    const res = await ask(await vg("viewer"), "What is Zephyr Ledger and who operates it?");
    const imported = (res.retrieved_source_ids ?? []).filter((s: string) => s.startsWith("imp_"));
    expect(imported.length, JSON.stringify(res.retrieved_source_ids)).toBeGreaterThan(0);
    for (const c of res.citations ?? []) {
      expect(res.retrieved_source_ids).toContain(c.id);
      if (c.id.startsWith("imp_")) expect(c.id).toMatch(/^imp_[0-9a-f]+#\d+$/);
    }
  });

  test("3.3 UI grounding pill matches the server response", async ({ page }) => {
    await page.addInitScript((t) => sessionStorage.setItem("veritasgraph_studio_token", t), TOKENS.viewer);
    await gotoStudio(page);
    await openSection(page, "Knowledge Graph", "graphrag");
    const model = page.locator("#graphModel");
    if (await model.locator(`option[value="${MODEL}"]`).count()) await model.selectOption(MODEL);
    await page.locator("#graphQuestion").fill("Who may approve vendor payments?");
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().endsWith("/graphrag/query") && r.request().method() === "POST", { timeout: 600_000 }),
      page.locator("#graphAsk").click(),
    ]);
    const body = await resp.json();
    const pill = page.locator("#graphGrounding");
    if (body.abstained) await expect(pill).toContainText(/abstain/i);
    else if (body.grounded) await expect(pill).toContainText(/grounded/i);
    else await expect(pill).toContainText(/not grounded/i);
    if (!body.citations?.length) {
      test.info().annotations.push({
        type: "citations-panel",
        description: (await page.locator("#graphCitations").innerText()).slice(0, 200),
      });
    }
  });

  test("3.4 no seed match abstains without calling the model", async () => {
    const t0 = Date.now();
    const res = await ask(await vg("viewer"), "What is the capital of France?");
    expect(res.abstained).toBe(true);
    expect(res.retrieved_source_ids ?? []).toEqual([]);
    expect(res.citations ?? []).toEqual([]);
    expect(Date.now() - t0).toBeLessThan(5_000);
  });

  test("3.5 vague question abstains", async () => {
    const res = await ask(await vg("viewer"), "Explain this");
    expect(res.abstained).toBe(true);
  });

  test("3.6 re-ingest counts only genuinely new entities (C7)", async () => {
    const editor = await vg("editor");
    const before = (await graph(editor)).nodes.length;
    const result = await ingest(editor, "SoD policy (again)", SOD_SAMPLE_DOC);
    const after = (await graph(editor)).nodes.length;
    test.info().annotations.push({ type: "re-ingest", description: `entities_added=${result.entities_added} growth=${after - before}` });
    expect(result.entities_added).toBe(after - before);
  });

  test("3.7 empty citations show the grounding explanation, not a generic empty state", async ({ page }) => {
    await page.addInitScript((t) => sessionStorage.setItem("veritasgraph_studio_token", t), TOKENS.viewer);
    await gotoStudio(page);
    await openSection(page, "Knowledge Graph", "graphrag");
    await page.locator("#graphQuestion").fill("What is the capital of France?");
    const [response] = await Promise.all([
      page.waitForResponse((r) => r.url().endsWith("/graphrag/query") && r.request().method() === "POST"),
      page.locator("#graphAsk").click(),
    ]);
    const body = await response.json();
    expect(body.citations).toEqual([]);
    const panel = page.locator("#graphCitations");
    await expect(panel).not.toContainText("No citations returned.");
    await expect(panel).toContainText(/Answer is not grounded/i);
  });
});
