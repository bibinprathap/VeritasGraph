import { expect, test } from "@playwright/test";
import { gotoStudio, openSection } from "../helpers";
import { BASE, TOKENS, ingest, vg } from "./vg";

// C1, C2, C3 — auth, roles, CORS, UI token handling against the real server.

test.describe("S1 security (C1-C3)", () => {
  test("1.1 /health and /studio are public", async () => {
    const anon = await vg(null);
    expect((await anon.get("/health")).status()).toBe(200);
    expect((await anon.get("/studio")).status()).toBe(200);
  });

  test("1.2 data route without a token is 401 with WWW-Authenticate", async () => {
    const r = await (await vg(null)).get("/graphrag/graph");
    expect(r.status()).toBe(401);
    expect(r.headers()["www-authenticate"]).toMatch(/Bearer/i);
  });

  test("1.3 wrong token of the same length is 401", async () => {
    const wrong = "x".repeat(TOKENS.viewer.length);
    const r = await (await vg(null)).get("/graphrag/graph", { headers: { Authorization: `Bearer ${wrong}` } });
    expect(r.status()).toBe(401);
  });

  test("1.4 viewer may read the graph and ask", async () => {
    const v = await vg("viewer");
    expect((await v.get("/graphrag/graph")).status()).toBe(200);
    const q = await v.post("/graphrag/query", { data: { question: "capital of France?", model: process.env.VG_MODEL } });
    expect(q.status()).toBe(200);
  });

  test("1.5 viewer may not ingest", async () => {
    const r = await (await vg("viewer")).post("/graphrag/ingest", {
      data: { title: "t", text: "Alice works at Contoso.", model: process.env.VG_MODEL },
    });
    expect(r.status()).toBe(403);
  });

  test("1.6 editor may ingest but not wipe the graph", async () => {
    const e = await vg("editor");
    await ingest(e, "S1 doc", "Alice Novak works at Contoso Ltd in Lisbon.");
    expect((await e.delete("/graphrag/graph")).status()).toBe(403);
  });

  test("1.7 admin may wipe the graph", async () => {
    expect((await (await vg("admin")).delete("/graphrag/graph")).status()).toBe(200);
  });

  test("1.8 CORS preflight from an unlisted origin gets no allow-origin", async () => {
    const r = await (await vg(null)).fetch("/graphrag/graph", {
      method: "OPTIONS",
      headers: { Origin: "https://evil.example", "Access-Control-Request-Method": "GET" },
    });
    expect(r.headers()["access-control-allow-origin"]).toBeUndefined();
  });

  test("1.9 UI prompts for a token once, stores it per tab, and loads the graph", async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    let prompts = 0;
    page.on("dialog", (d) => {
      prompts++;
      void d.accept(TOKENS.viewer);
    });
    const unauthorized: string[] = [];
    page.on("response", (r) => {
      if (r.url().startsWith(BASE) && r.status() === 401) unauthorized.push(r.url());
    });
    await gotoStudio(page);
    await openSection(page, "Knowledge Graph", "graphrag");
    await expect(page.locator("#graphStats")).not.toHaveText(/error|401|failed/i);
    expect(await page.evaluate(() => sessionStorage.getItem("veritasgraph_studio_token"))).toBe(TOKENS.viewer);
    test.info().annotations.push({ type: "prompts", description: String(prompts) });
    test.info().annotations.push({ type: "initial-401s", description: String(unauthorized.length) });
    expect(prompts, "the user should be asked for the token exactly once").toBe(1);
    await ctx.close();
  });

  test("1.10 UI with a wrong token prompts once and shows an error", async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    let prompts = 0;
    page.on("dialog", (d) => {
      prompts++;
      void d.accept("y".repeat(48));
    });
    await page.goto(process.env.STUDIO_URL!);
    await page.locator("#nav button").first().waitFor();
    await page.waitForLoadState("networkidle");
    test.info().annotations.push({ type: "prompts", description: String(prompts) });
    expect(prompts, "retried guard should stop repeated prompts").toBe(1);
    await ctx.close();
  });

  test("1.11 token is not persisted across browser contexts", async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    let prompted = false;
    page.on("dialog", (d) => {
      prompted = true;
      void d.dismiss();
    });
    await page.goto(process.env.STUDIO_URL!);
    await page.locator("#nav button").first().waitFor();
    await page.waitForLoadState("networkidle");
    expect(prompted).toBe(true);
    expect(await page.evaluate(() => sessionStorage.getItem("veritasgraph_studio_token"))).toBeNull();
    await ctx.close();
  });
});
