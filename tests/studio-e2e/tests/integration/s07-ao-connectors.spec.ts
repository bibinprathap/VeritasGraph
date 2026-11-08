import { expect, test } from "@playwright/test";
import { AO_VIEWER_TOKEN, ENGINES, ao, aoAsk, aoResult, blockedUnlessAo } from "./ao";

// S7 — Auto-Ontology connectors, all ten engines, golden revenue per engine.

const engineReason = (e: (typeof ENGINES)[number]) =>
  process.env[e.env] ? null : `${e.key}: ${e.env} unset (engine not provisioned/seeded for this run)`;

test.describe("S7a connectors via CONNECTION_STRINGS (profile A)", () => {
  test("7a.1 AO reports CONNECTION_STRINGS as the source", async () => {
    await blockedUnlessAo(process.env.AO_PROFILE === "A" ? null : "AO_PROFILE != A");
    const r = await (await ao()).get("/api/connections/source");
    expect(r.status()).toBe(200);
    expect(JSON.stringify(await r.json())).toMatch(/env|CONNECTION_STRINGS/i);
  });

  for (const e of ENGINES) {
    test.describe(`connector: ${e.key}`, () => {
      test(`7a.2 ${e.key} catalog ingested`, async () => {
        await blockedUnlessAo(engineReason(e));
        const dbs = await (await (await ao()).get("/api/datasources/dbs")).json();
        expect(JSON.stringify(dbs)).toContain(e.db);
      });

      test(`7a.3 ${e.key} golden revenue = ${e.golden.toFixed(2)}`, async () => {
        await blockedUnlessAo(engineReason(e));
        const ev = await aoAsk(await ao(), `What was revenue for ${e.product} in Pennsylvania in June 2015?`);
        expect(ev.find((x) => x.type === "error")).toBeUndefined();
        const a = aoResult(ev);
        expect(a.sql_code).toMatch(/invoice_lines/i);
        const nums = (JSON.stringify(a.sql_response_from_db).match(/\d+(\.\d+)?/g) ?? []).map(Number);
        expect(nums.some((n) => Math.abs(n - e.golden) < 0.005), JSON.stringify(a.sql_response_from_db)).toBe(true);
        expect(a.response).toContain(e.golden.toFixed(2));
      });
    });
  }
});

test.describe("S7b connectors via UI (profile B)", () => {
  test("7b.4 connection list never leaks secrets", async () => {
    await blockedUnlessAo(process.env.AO_PROFILE === "B" ? null : "AO_PROFILE != B");
    const body = await (await (await ao()).get("/api/connections")).text();
    expect(body).not.toMatch(/password|dapi[0-9a-f]{8}|eyJ[a-zA-Z0-9_-]{10,}\./);
  });

  test("7b.7 viewer cannot create connections", async () => {
    await blockedUnlessAo(AO_VIEWER_TOKEN ? null : "AO_VIEWER_API_TOKEN unset");
    const r = await (await ao(AO_VIEWER_TOKEN)).post("/api/connections", { data: {} });
    expect(r.status()).toBe(403);
  });

  for (const e of ENGINES.filter((x) => x.ui)) {
    test(`7b.2-7b.9 ${e.key} test/save/ask/delete through Settings → Connections`, async () => {
      await blockedUnlessAo(process.env.AO_PROFILE === "B" ? engineReason(e) : "AO_PROFILE != B");
      test.fixme(true, "UI form selectors for each engine are not yet recorded against a live AO");
    });
  }
});
