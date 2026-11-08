# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: s03-citations.spec.ts >> S3 citations and abstention (C4-C7) >> 3.7 empty citations show the grounding explanation, not a generic empty state
- Location: tests/integration/s03-citations.spec.ts:98:3

# Error details

```
Error: expect(locator).not.toContainText(expected) failed

Locator: locator('#graphCitations')
Expected substring: not "No citations returned."
Received string: "No citations returned."
Timeout: 60000ms

Call log:
  - Expect "not toContainText" with timeout 60000ms
  - waiting for locator('#graphCitations')
    123 × locator resolved to <div class="list" id="graphCitations">…</div>
        - unexpected value "No citations returned."

```

```yaml
- text: No citations returned.
```

# Test source

```ts
  10  |     { id: "n1", name: "Zephyr Ledger", type: "system", description: "Zephyr Ledger is the general-ledger system of record used by the finance team." },
  11  |     { id: "n2", name: "Finance Team", type: "organization", description: "The finance team owns month-end close." },
  12  |   ],
  13  |   edges: [{ source: "n1", target: "n2", description: "Zephyr Ledger is operated by the Finance Team." }],
  14  | };
  15  | 
  16  | test.describe("S3 citations and abstention (C4-C7)", () => {
  17  |   test.beforeAll(async () => {
  18  |     expect((await (await vg("admin")).delete("/graphrag/graph")).status()).toBe(200);
  19  |     const editor = await vg("editor");
  20  |     await ingest(editor, "SoD policy", SOD_SAMPLE_DOC);
  21  |     const imp = await editor.post("/graphrag/import", {
  22  |       data: { graph: IMPORTED, format: "auto", title: "Imported finance systems" },
  23  |     });
  24  |     expect(imp.status(), await imp.text()).toBe(200);
  25  |   });
  26  | 
  27  |   test("3.1 every citation was retrieved; grounded matches citations (3 runs)", async () => {
  28  |     const viewer = await vg("viewer");
  29  |     for (let i = 0; i < 3; i++) {
  30  |       const res = await ask(viewer, "Who may approve vendor payments and what conflicts must be avoided?");
  31  |       const retrieved = new Set<string>(res.retrieved_source_ids ?? []);
  32  |       for (const c of res.citations ?? []) expect(retrieved, `citation ${c.id} was not retrieved`).toContain(c.id);
  33  |       if (!res.abstained) expect(res.grounded).toBe((res.citations ?? []).length > 0);
  34  |       test.info().annotations.push({
  35  |         type: `run${i + 1}`,
  36  |         description: `abstained=${res.abstained} grounded=${res.grounded} citations=${(res.citations ?? []).length} unknown=${(res.unknown_citations ?? []).length}`,
  37  |       });
  38  |     }
  39  |   });
  40  | 
  41  |   test("3.2 imported facts are retrievable under imp_ ids", async () => {
  42  |     const res = await ask(await vg("viewer"), "What is Zephyr Ledger and who operates it?");
  43  |     const imported = (res.retrieved_source_ids ?? []).filter((s: string) => s.startsWith("imp_"));
  44  |     expect(imported.length, JSON.stringify(res.retrieved_source_ids)).toBeGreaterThan(0);
  45  |     for (const c of res.citations ?? []) {
  46  |       expect(res.retrieved_source_ids).toContain(c.id);
  47  |       if (c.id.startsWith("imp_")) expect(c.id).toMatch(/^imp_[0-9a-f]+#\d+$/);
  48  |     }
  49  |   });
  50  | 
  51  |   test("3.3 UI grounding pill matches the server response", async ({ page }) => {
  52  |     await page.addInitScript((t) => sessionStorage.setItem("veritasgraph_studio_token", t), TOKENS.viewer);
  53  |     await gotoStudio(page);
  54  |     await openSection(page, "Knowledge Graph", "graphrag");
  55  |     const model = page.locator("#graphModel");
  56  |     if (await model.locator(`option[value="${MODEL}"]`).count()) await model.selectOption(MODEL);
  57  |     await page.locator("#graphQuestion").fill("Who may approve vendor payments?");
  58  |     const [resp] = await Promise.all([
  59  |       page.waitForResponse((r) => r.url().endsWith("/graphrag/query") && r.request().method() === "POST", { timeout: 600_000 }),
  60  |       page.locator("#graphAsk").click(),
  61  |     ]);
  62  |     const body = await resp.json();
  63  |     const pill = page.locator("#graphGrounding");
  64  |     if (body.abstained) await expect(pill).toContainText(/abstain/i);
  65  |     else if (body.grounded) await expect(pill).toContainText(/grounded/i);
  66  |     else await expect(pill).toContainText(/not grounded/i);
  67  |     if (!body.citations?.length) {
  68  |       test.info().annotations.push({
  69  |         type: "citations-panel",
  70  |         description: (await page.locator("#graphCitations").innerText()).slice(0, 200),
  71  |       });
  72  |     }
  73  |   });
  74  | 
  75  |   test("3.4 no seed match abstains without calling the model", async () => {
  76  |     const t0 = Date.now();
  77  |     const res = await ask(await vg("viewer"), "What is the capital of France?");
  78  |     expect(res.abstained).toBe(true);
  79  |     expect(res.retrieved_source_ids ?? []).toEqual([]);
  80  |     expect(res.citations ?? []).toEqual([]);
  81  |     expect(Date.now() - t0).toBeLessThan(5_000);
  82  |   });
  83  | 
  84  |   test("3.5 vague question abstains", async () => {
  85  |     const res = await ask(await vg("viewer"), "Explain this");
  86  |     expect(res.abstained).toBe(true);
  87  |   });
  88  | 
  89  |   test("3.6 re-ingest counts only genuinely new entities (C7)", async () => {
  90  |     const editor = await vg("editor");
  91  |     const before = (await graph(editor)).nodes.length;
  92  |     const result = await ingest(editor, "SoD policy (again)", SOD_SAMPLE_DOC);
  93  |     const after = (await graph(editor)).nodes.length;
  94  |     test.info().annotations.push({ type: "re-ingest", description: `entities_added=${result.entities_added} growth=${after - before}` });
  95  |     expect(result.entities_added).toBe(after - before);
  96  |   });
  97  | 
  98  |   test("3.7 empty citations show the grounding explanation, not a generic empty state", async ({ page }) => {
  99  |     await page.addInitScript((t) => sessionStorage.setItem("veritasgraph_studio_token", t), TOKENS.viewer);
  100 |     await gotoStudio(page);
  101 |     await openSection(page, "Knowledge Graph", "graphrag");
  102 |     await page.locator("#graphQuestion").fill("What is the capital of France?");
  103 |     const [response] = await Promise.all([
  104 |       page.waitForResponse((r) => r.url().endsWith("/graphrag/query") && r.request().method() === "POST"),
  105 |       page.locator("#graphAsk").click(),
  106 |     ]);
  107 |     const body = await response.json();
  108 |     expect(body.citations).toEqual([]);
  109 |     const panel = page.locator("#graphCitations");
> 110 |     await expect(panel).not.toContainText("No citations returned.");
      |                             ^ Error: expect(locator).not.toContainText(expected) failed
  111 |     await expect(panel).toContainText(/Answer is not grounded/i);
  112 |   });
  113 | });
  114 | 
```