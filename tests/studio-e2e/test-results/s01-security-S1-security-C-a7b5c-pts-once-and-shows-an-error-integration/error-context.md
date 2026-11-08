# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: s01-security.spec.ts >> S1 security (C1-C3) >> 1.10 UI with a wrong token prompts once and shows an error
- Location: tests/integration/s01-security.spec.ts:80:3

# Error details

```
Error: retried guard should stop repeated prompts

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
      - button "Knowledge Graph" [ref=e36] [cursor=pointer]:
        - generic [ref=e38]: Knowledge Graph
      - button "Ontology" [ref=e39] [cursor=pointer]:
        - generic [ref=e41]: Ontology
    - generic [ref=e42]:
      - text: "Runtime status: Healthy"
      - text: "Last build: —"
  - main [ref=e43]:
    - generic [ref=e44]:
      - generic [ref=e45]:
        - heading "Agent Studio" [level=1] [ref=e46]
        - paragraph [ref=e47]: Build and operate enterprise agents with linked tools and governed knowledge.
      - generic [ref=e48]:
        - button "Save draft" [ref=e49] [cursor=pointer]
        - button "Deploy workspace" [ref=e50] [cursor=pointer]
    - generic [ref=e51]:
      - generic [ref=e52]:
        - generic [ref=e53]:
          - generic [ref=e54]: Active agents
          - strong [ref=e55]: —
        - generic [ref=e56]:
          - generic [ref=e57]: Connected tools
          - strong [ref=e58]: —
        - generic [ref=e59]:
          - generic [ref=e60]: Eval pass rate
          - strong [ref=e61]: —
        - generic [ref=e62]:
          - generic [ref=e63]: Guardrail blocks
          - strong [ref=e64]: —
      - generic [ref=e66]:
        - article [ref=e67]:
          - heading "Agent builder" [level=3] [ref=e68]
          - paragraph [ref=e69]: Design role, model, and operating policy for each agent.
          - generic [ref=e70]:
            - textbox "Agent name" [ref=e71]
            - combobox [ref=e72]:
              - option "No local models found" [disabled] [selected]
          - textbox "System instructions and behavior profile" [ref=e73]
          - generic [ref=e74]:
            - generic [ref=e75]: Wire studio capabilities into this agent
            - generic [ref=e76]:
              - generic [ref=e77] [cursor=pointer]:
                - checkbox "Knowledge Graph" [ref=e78]
                - text: Knowledge Graph
              - generic [ref=e79] [cursor=pointer]:
                - checkbox "Tools" [ref=e80]
                - text: Tools
              - generic [ref=e81] [cursor=pointer]:
                - checkbox "Memory" [ref=e82]
                - text: Memory
              - generic [ref=e83] [cursor=pointer]:
                - checkbox "Guardrails" [ref=e84]
                - text: Guardrails
              - generic [ref=e85] [cursor=pointer]:
                - checkbox "Data log" [ref=e86]
                - text: Data log
            - generic [ref=e87]:
              - generic [ref=e88]: Veritasroom context budget (tokens)
              - spinbutton "Veritasroom context budget (tokens)" [ref=e89]: "600"
          - generic [ref=e90]:
            - textbox "Tags (comma separated)" [ref=e91]
            - button "Create agent" [ref=e92] [cursor=pointer]
        - article [ref=e93]:
          - heading "Orchestration map" [level=3] [ref=e94]
          - paragraph [ref=e95]: Plan handoffs, escalation rules, and confidence gates.
          - img [ref=e98]
          - paragraph [ref=e100]: Signal shows successful tool-driven completions over recent sessions. Use this to tune agent routing before release.
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
  76  |     expect(prompts, "the user should be asked for the token exactly once").toBe(1);
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
> 92  |     expect(prompts, "retried guard should stop repeated prompts").toBe(1);
      |                                                                   ^ Error: retried guard should stop repeated prompts
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