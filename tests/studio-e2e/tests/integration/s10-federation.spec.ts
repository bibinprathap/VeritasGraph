import { expect, test } from "@playwright/test";
import { AO_URL, blockedUnlessAo } from "./ao";
import { vg } from "./vg";

// S10 — federation (Phase 8). Not implemented in VeritasGraph yet: fixme.

test.describe("S10 federation", () => {
  test("10.1 AO tool is refused until AO's network is allowlisted", async () => {
    await blockedUnlessAo();
    const editor = await vg("editor");
    const created = await editor.post("/tools", {
      data: { name: "Auto-Ontology", config: { endpoint: `${AO_URL}/api/health`, method: "GET" } },
    });
    const id = (await created.json()).item.id;
    const res = await (await editor.post(`/tools/${id}/test`)).json();
    // AO_URL normally resolves to loopback or a private address.
    expect(res.ok).toBe(false);
  });

  test("10.3 one Playground answer combines AO SQL and a VG citation", async () => {
    test.fixme(true, "Phase 8 not implemented: no Auto-Ontology tool kind in Studio");
  });

  test("10.4/10.5 AO model export imports into VG as proposed terms", async () => {
    test.fixme(true, "Phase 8 not implemented: VG has no /interchange/import route");
  });

  test("10.6 Studio uses AO MCP via OAuth", async () => {
    test.fixme(true, "Studio has no OAuth MCP client");
  });
});
