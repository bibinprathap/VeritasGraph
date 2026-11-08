import { expect, test } from "@playwright/test";
import { ask, graph, ingest, mcp, toolResult, vg } from "./vg";

// C14-C19 — governed vocabulary, certification by admins only, type/predicate
// mapping of real LLM extraction, answerability, governed abstention, receipts.

const QUESTION = "Which supplier does Acme use and what is their ad spend?";

async function snapshot() {
  const r = await (await vg("viewer")).get("/ontology");
  expect(r.status()).toBe(200);
  return r.json() as Promise<{
    types: { name: string; status: string }[];
    predicates: { name: string; status: string }[];
    terms: { id: string; name: string; status: string }[];
  }>;
}

const certifiedNames = (rows: { name: string; status: string }[]) =>
  rows.filter((r) => r.status === "certified").map((r) => r.name).sort();

test.describe("S6 ontology and governed answers (C14-C19)", () => {
  test.beforeAll(async () => {
    expect((await (await vg("admin")).delete("/graphrag/graph")).status()).toBe(200);
  });

  test("6.1 editors propose, only admins certify", async () => {
    const editor = await vg("editor");
    for (const [path, data] of [
      ["/ontology/types", { name: "organization", description: "A company or institution", synonyms: ["company", "corporation", "firm"] }],
      ["/ontology/types", { name: "person", description: "A human being", synonyms: ["employee", "engineer"] }],
      ["/ontology/predicates", { name: "employs", description: "Organization employs person", domain_type: "organization", range_type: "person", synonyms: ["hires"] }],
      ["/ontology/terms", { name: "Vendor", definition: "An external party that supplies goods or services.", synonyms: ["supplier"] }],
    ] as const) {
      const r = await editor.post(path, { data });
      expect(r.status(), `${path}: ${await r.text()}`).toBe(200);
    }
    expect((await (await vg("viewer")).post("/ontology/types/organization/certify")).status()).toBe(403);
    expect((await editor.post("/ontology/types/organization/certify")).status()).toBe(403);
    const admin = await vg("admin");
    for (const p of ["/ontology/types/organization/certify", "/ontology/types/person/certify", "/ontology/predicates/employs/certify"]) {
      const r = await admin.post(p);
      expect(r.status(), `${p}: ${await r.text()}`).toBe(200);
    }
    const snap = await snapshot();
    expect(certifiedNames(snap.types)).toEqual(["organization", "person"]);
    expect(certifiedNames(snap.predicates)).toEqual(["employs"]);
    expect(snap.terms.find((t) => t.name === "Vendor")?.status).toBe("proposed");
  });

  test("6.2 real extraction is mapped onto the certified vocabulary", async () => {
    await ingest(await vg("editor"), "Acme", "Acme Corp is a company that employs Bob Smith, an engineer. Acme Corp buys steel from Fenwick Metals, its main supplier.");
    const g = await graph(await vg("viewer"));
    const types = new Set(g.nodes.map((n) => n.type));
    for (const t of types) expect(["organization", "person", "concept"]).toContain(t);
    for (const e of g.edges) expect([null, "employs"]).toContain(e.predicate);
    const acme = g.nodes.find((n) => /acme/i.test(n.name));
    expect(acme, g.nodes.map((n) => `${n.name}:${n.type}`).join(", ")).toBeDefined();
    test.info().annotations.push({ type: "extraction", description: g.nodes.map((n) => `${n.name}:${n.type}`).join(", ") });
    expect(acme!.type).toBe("organization");
  });

  test("6.3 unmapped extraction becomes proposals, never certified", async () => {
    await ingest(await vg("editor"), "Starship", "The starship Valiant carries Bob Smith to the orbital station Helios.");
    const snap = await snapshot();
    expect(certifiedNames(snap.types)).toEqual(["organization", "person"]);
    expect(certifiedNames(snap.predicates)).toEqual(["employs"]);
    const g = await graph(await vg("viewer"));
    for (const n of g.nodes) expect(["organization", "person", "concept"]).toContain(n.type);
    test.info().annotations.push({
      type: "proposals",
      description: [...snap.types, ...snap.predicates].filter((x) => x.status === "proposed").map((x) => x.name).join(", "),
    });
  });

  test("6.4 answerability reports coverage and uncovered words", async () => {
    const r = mcp("read", [
      { method: "initialize", params: {} },
      { method: "tools/call", params: { name: "veritasgraph_check_answerable", arguments: { question: QUESTION } } },
    ]);
    const res = toolResult(r.responses[1]);
    expect(res.matched_entities.some((e: { name: string }) => /acme/i.test(e.name)), JSON.stringify(res)).toBe(true);
    expect(res.matched_terms.map((t: { name: string }) => t.name)).toContain("Vendor");
    expect(res.unmatched_tokens).toContain("spend");
    expect(res.coverage).toBeLessThan(1);
    expect(res.answerable).toBe(true);
  });

  test("6.5 governed mode abstains on a proposed-only term, then answers after certification", async () => {
    const viewer = await vg("viewer");
    const gate = await (await viewer.post("/graphrag/answerable", { data: { question: QUESTION, mode: "governed" } })).json();
    expect(gate.answerable).toBe(false);
    expect(gate.reason).toMatch(/certified/i);

    const before = await ask(viewer, QUESTION, "governed");
    expect(before.abstained).toBe(true);

    expect((await (await vg("admin")).post("/ontology/terms/Vendor/certify")).status()).toBe(200);
    const after = await (await viewer.post("/graphrag/answerable", { data: { question: QUESTION, mode: "governed" } })).json();
    expect(after.answerable, JSON.stringify(after)).toBe(true);

    const res = await ask(viewer, QUESTION, "governed");
    test.info().annotations.push({
      type: "governed",
      description: `abstained=${res.abstained} reason=${res.abstain_reason ?? ""} grounded=${res.grounded} citations=${(res.citations ?? []).length}`,
    });
    if (!res.abstained) {
      expect(res.grounded).toBe(true);
      expect((res.citations ?? []).length).toBeGreaterThan(0);
    }
    const id = res.answer_id ?? before.answer_id;
    expect(id, "query must return an answer_id receipt").toBeTruthy();
    const receipt = await viewer.get(`/graphrag/answers/${id}`);
    expect(receipt.status()).toBe(200);
    expect((await receipt.json()).graph_version).toBeDefined();
  });

  test("6.6 MCP agents can propose terms but never certify", async () => {
    const r = mcp("write", [
      { method: "initialize", params: {} },
      { method: "tools/list" },
      {
        method: "tools/call",
        params: { name: "veritasgraph_propose_term", arguments: { name: "Ad Spend", definition: "Money spent on advertising.", synonyms: ["advertising spend"] } },
      },
    ]);
    const tools = (r.responses[1].result.tools as { name: string }[]).map((t) => t.name);
    expect(tools.filter((t) => /certify|deprecate/.test(t))).toEqual([]);
    expect(r.responses[2].result.isError, r.responses[2].result.content?.[0]?.text).toBeFalsy();
    const term = (await snapshot()).terms.find((t) => t.name === "Ad Spend");
    expect(term?.status).toBe("proposed");
  });

  test("6.7 deprecating a type is admin-only and removes it from mapping", async () => {
    expect((await (await vg("editor")).post("/ontology/types/person/deprecate")).status()).toBe(403);
    expect((await (await vg("admin")).post("/ontology/types/person/deprecate")).status()).toBe(200);
    expect(certifiedNames((await snapshot()).types)).toEqual(["organization"]);
  });
});
