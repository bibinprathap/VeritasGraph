# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: s01-security.spec.ts >> S1 security (C1-C3) >> 1.9 UI prompts for a token once, stores it per tab, and loads the graph
- Location: tests/integration/s01-security.spec.ts:58:3

# Error details

```
Error: the user should be asked for the token exactly once

expect(received).toBe(expected) // Object.is equality

Expected: 1
Received: 11
```

# Page snapshot

```yaml
- generic [ref=e2]:
  - complementary [ref=e3]:
    - generic [ref=e4]:
      - generic [ref=e5]: VG
      - generic [ref=e6]:
        - strong [ref=e7]: VeritasGraph Studio
        - text: Agent Build Workspace
    - generic [ref=e8]:
      - button "Agents" [ref=e9] [cursor=pointer]:
        - generic [ref=e11]: Agents
      - button "Tools" [ref=e12] [cursor=pointer]:
        - generic [ref=e14]: Tools
      - button "Knowledge" [ref=e15] [cursor=pointer]:
        - generic [ref=e17]: Knowledge
      - button "Guardrails" [ref=e18] [cursor=pointer]:
        - generic [ref=e20]: Guardrails
      - button "Memory" [ref=e21] [cursor=pointer]:
        - generic [ref=e23]: Memory
      - button "Data" [ref=e24] [cursor=pointer]:
        - generic [ref=e26]: Data
      - button "Evaluation" [ref=e27] [cursor=pointer]:
        - generic [ref=e29]: Evaluation
      - button "Fine-tune" [ref=e30] [cursor=pointer]:
        - generic [ref=e32]: Fine-tune
      - button "Playground" [ref=e33] [cursor=pointer]:
        - generic [ref=e35]: Playground
      - button "Knowledge Graph" [active] [ref=e36] [cursor=pointer]:
        - generic [ref=e38]: Knowledge Graph
      - button "Ontology" [ref=e39] [cursor=pointer]:
        - generic [ref=e41]: Ontology
    - generic [ref=e42]:
      - text: "Runtime status: Healthy"
      - text: "Last build: no deploys yet"
  - main [ref=e43]:
    - generic [ref=e44]:
      - generic [ref=e45]:
        - heading "Knowledge Graph" [level=1] [ref=e46]
        - paragraph [ref=e47]: Build a VeritasGraph knowledge graph and reason over it with citations.
      - generic [ref=e48]:
        - button "Save draft" [ref=e49] [cursor=pointer]
        - button "Deploy workspace" [ref=e50] [cursor=pointer]
    - generic [ref=e51]:
      - generic [ref=e52]:
        - generic [ref=e53]:
          - generic [ref=e54]: Active agents
          - strong [ref=e55]: "4"
        - generic [ref=e56]:
          - generic [ref=e57]: Connected tools
          - strong [ref=e58]: "3"
        - generic [ref=e59]:
          - generic [ref=e60]: Eval pass rate
          - strong [ref=e61]: 0%
        - generic [ref=e62]:
          - generic [ref=e63]: Guardrail blocks
          - strong [ref=e64]: "12"
      - generic [ref=e65]:
        - generic [ref=e66]:
          - article [ref=e67]:
            - heading "Upload a knowledge graph" [level=3] [ref=e68]
            - paragraph [ref=e69]:
              - text: Import a pre-built graph from
              - strong [ref=e70]: Graphify
              - text: ","
              - strong [ref=e71]: Understand-Anything
              - text: ", an"
              - strong [ref=e72]: AI Atlas
              - text: taxonomy, or any node/edge JSON. Imported content is tagged with provenance so curated edges stay distinguishable from extracted/inferred ones.
            - generic [ref=e73]:
              - combobox "Source format" [ref=e74]:
                - option "Auto-detect format" [selected]
                - option "Graphify (graph.json)"
                - option "Understand-Anything"
                - option "AI Atlas taxonomy"
                - option "Generic JSON (nodes/edges)"
              - combobox "Provenance tag" [ref=e75]:
                - option "Curated (authoritative)" [selected]
                - option "Extracted"
                - option "Inferred (suggested)"
              - combobox "Merge strategy" [ref=e76]:
                - option "Preserve curated on conflict" [selected]
                - option "Skip existing"
                - option "Overwrite existing"
            - generic [ref=e77]:
              - button "Choose File" [ref=e78]
              - button "Import graph" [ref=e79] [cursor=pointer]
          - article [ref=e80]:
            - heading "Build knowledge graph" [level=3] [ref=e81]
            - paragraph [ref=e82]: Paste a document. A local model extracts entities and relationships with verifiable source attribution.
            - generic [ref=e83]:
              - combobox [ref=e84]:
                - option "llama3.1-12k:latest" [selected]
                - option "nomic-embed-text:latest"
                - option "llama3.1:8b"
                - option "glm-4.7-flash:latest"
              - button "Clear graph" [ref=e85] [cursor=pointer]
            - textbox "Document title" [ref=e86]
            - textbox "Paste document text to extract a knowledge graph..." [ref=e87]
            - generic [ref=e88]:
              - generic [ref=e89]: No graph yet.
              - button "Ingest document" [ref=e90] [cursor=pointer]
          - article [ref=e91]:
            - heading "Graph explorer" [level=3] [ref=e92]
            - paragraph [ref=e93]: Entities are nodes, relationships are edges. Hover a node for details.
            - img [ref=e94]:
              - generic [ref=e95]: Ingest a document to build the graph
        - generic [ref=e97]:
          - article [ref=e98]:
            - heading "Graph-grounded reasoning" [level=3] [ref=e99]
            - paragraph [ref=e100]: Ask a question. The answer uses multi-hop reasoning over the graph and cites its sources.
            - generic [ref=e101]:
              - textbox "Ask about the ingested documents..." [ref=e102]
              - button "Reason" [ref=e103] [cursor=pointer]
            - generic [ref=e104]:
              - checkbox "Governed mode (answer only from certified terms; withhold ungrounded answers)" [ref=e105]
              - text: Governed mode (answer only from certified terms; withhold ungrounded answers)
          - article [ref=e107]:
            - heading "Reasoning path & citations" [level=3] [ref=e108]
            - paragraph [ref=e109]: The multi-hop chain and verifiable sources behind the latest answer.
```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | import { gotoStudio, openSection } from "../helpers";
  3   | import { BASE, TOKENS, ingest, vg } from "./vg";
  4   | 
  5   | // C1, C2, C3 — auth, roles, CORS, UI token handling against the real server.
  6   | 
  7   | test.describe("S1 security (C1-C3)", () => {
  8   |   test("1.1 /health and /studio are public", async () => {
  9   |     const anon = await vg(null);
  10  |     expect((await anon.get("/health")).status()).toBe(200);
  11  |     expect((await anon.get("/studio")).status()).toBe(200);
  12  |   });
  13  | 
  14  |   test("1.2 data route without a token is 401 with WWW-Authenticate", async () => {
  15  |     const r = await (await vg(null)).get("/graphrag/graph");
  16  |     expect(r.status()).toBe(401);
  17  |     expect(r.headers()["www-authenticate"]).toMatch(/Bearer/i);
  18  |   });
  19  | 
  20  |   test("1.3 wrong token of the same length is 401", async () => {
  21  |     const wrong = "x".repeat(TOKENS.viewer.length);
  22  |     const r = await (await vg(null)).get("/graphrag/graph", { headers: { Authorization: `Bearer ${wrong}` } });
  23  |     expect(r.status()).toBe(401);
  24  |   });
  25  | 
  26  |   test("1.4 viewer may read the graph and ask", async () => {
  27  |     const v = await vg("viewer");
  28  |     expect((await v.get("/graphrag/graph")).status()).toBe(200);
  29  |     const q = await v.post("/graphrag/query", { data: { question: "capital of France?", model: process.env.VG_MODEL } });
  30  |     expect(q.status()).toBe(200);
  31  |   });
  32  | 
  33  |   test("1.5 viewer may not ingest", async () => {
  34  |     const r = await (await vg("viewer")).post("/graphrag/ingest", {
  35  |       data: { title: "t", text: "Alice works at Contoso.", model: process.env.VG_MODEL },
  36  |     });
  37  |     expect(r.status()).toBe(403);
  38  |   });
  39  | 
  40  |   test("1.6 editor may ingest but not wipe the graph", async () => {
  41  |     const e = await vg("editor");
  42  |     await ingest(e, "S1 doc", "Alice Novak works at Contoso Ltd in Lisbon.");
  43  |     expect((await e.delete("/graphrag/graph")).status()).toBe(403);
  44  |   });
  45  | 
  46  |   test("1.7 admin may wipe the graph", async () => {
  47  |     expect((await (await vg("admin")).delete("/graphrag/graph")).status()).toBe(200);
  48  |   });
  49  | 
  50  |   test("1.8 CORS preflight from an unlisted origin gets no allow-origin", async () => {
  51  |     const r = await (await vg(null)).fetch("/graphrag/graph", {
  52  |       method: "OPTIONS",
  53  |       headers: { Origin: "https://evil.example", "Access-Control-Request-Method": "GET" },
  54  |     });
  55  |     expect(r.headers()["access-control-allow-origin"]).toBeUndefined();
  56  |   });
  57  | 
  58  |   test("1.9 UI prompts for a token once, stores it per tab, and loads the graph", async ({ browser }) => {
  59  |     const ctx = await browser.newContext();
  60  |     const page = await ctx.newPage();
  61  |     let prompts = 0;
  62  |     page.on("dialog", (d) => {
  63  |       prompts++;
  64  |       void d.accept(TOKENS.viewer);
  65  |     });
  66  |     const unauthorized: string[] = [];
  67  |     page.on("response", (r) => {
  68  |       if (r.url().startsWith(BASE) && r.status() === 401) unauthorized.push(r.url());
  69  |     });
  70  |     await gotoStudio(page);
  71  |     await openSection(page, "Knowledge Graph", "graphrag");
  72  |     await expect(page.locator("#graphStats")).not.toHaveText(/error|401|failed/i);
  73  |     expect(await page.evaluate(() => sessionStorage.getItem("veritasgraph_studio_token"))).toBe(TOKENS.viewer);
  74  |     test.info().annotations.push({ type: "prompts", description: String(prompts) });
  75  |     test.info().annotations.push({ type: "initial-401s", description: String(unauthorized.length) });
> 76  |     expect(prompts, "the user should be asked for the token exactly once").toBe(1);
      |                                                                            ^ Error: the user should be asked for the token exactly once
  77  |     await ctx.close();
  78  |   });
  79  | 
  80  |   test("1.10 UI with a wrong token prompts once and shows an error", async ({ browser }) => {
  81  |     const ctx = await browser.newContext();
  82  |     const page = await ctx.newPage();
  83  |     let prompts = 0;
  84  |     page.on("dialog", (d) => {
  85  |       prompts++;
  86  |       void d.accept("y".repeat(48));
  87  |     });
  88  |     await page.goto(process.env.STUDIO_URL!);
  89  |     await page.locator("#nav button").first().waitFor();
  90  |     await page.waitForLoadState("networkidle");
  91  |     test.info().annotations.push({ type: "prompts", description: String(prompts) });
  92  |     expect(prompts, "retried guard should stop repeated prompts").toBe(1);
  93  |     await ctx.close();
  94  |   });
  95  | 
  96  |   test("1.11 token is not persisted across browser contexts", async ({ browser }) => {
  97  |     const ctx = await browser.newContext();
  98  |     const page = await ctx.newPage();
  99  |     let prompted = false;
  100 |     page.on("dialog", (d) => {
  101 |       prompted = true;
  102 |       void d.dismiss();
  103 |     });
  104 |     await page.goto(process.env.STUDIO_URL!);
  105 |     await page.locator("#nav button").first().waitFor();
  106 |     await page.waitForLoadState("networkidle");
  107 |     expect(prompted).toBe(true);
  108 |     expect(await page.evaluate(() => sessionStorage.getItem("veritasgraph_studio_token"))).toBeNull();
  109 |     await ctx.close();
  110 |   });
  111 | });
  112 | 
```