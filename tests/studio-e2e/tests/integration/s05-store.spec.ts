import { expect, test } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { MODEL, graph, ingest, mcpAsync, startStudio, vg } from "./vg";

// C12, C13 — one SQLite store shared by Studio and MCP processes; legacy JSON migrates.

const mcpIngest = (title: string, text: string) =>
  mcpAsync("write", [
    { method: "initialize", params: {} },
    { method: "tools/call", params: { name: "veritasgraph_ingest_document", arguments: { title, text, model: MODEL } } },
  ]);

test.describe("S5 shared store (C12, C13)", () => {
  test.beforeAll(async () => {
    expect((await (await vg("admin")).delete("/graphrag/graph")).status()).toBe(200);
  });

  test("5.1 concurrent Studio + MCP ingests both survive (3 iterations)", async () => {
    const editor = await vg("editor");
    for (let i = 1; i <= 3; i++) {
      const [, viaMcp] = await Promise.all([
        ingest(editor, `Orion ${i}`, `Orion Freight ${i} is a logistics company in Rotterdam founded by Mara Velden.`),
        mcpIngest(`Kestrel ${i}`, `Kestrel Biotech ${i} is a pharmaceutical firm in Basel that employs Ilse Brandt.`),
      ]);
      expect(viaMcp.status, viaMcp.stderr).toBe(0);
      expect(viaMcp.stderr).not.toMatch(/database is locked/i);
      expect(viaMcp.responses[1].result?.isError, viaMcp.responses[1].result?.content?.[0]?.text).toBeFalsy();
    }
    const names = (await graph(editor)).nodes.map((n) => n.name.toLowerCase());
    expect(names.some((n) => n.includes("orion")), names.join(", ")).toBe(true);
    expect(names.some((n) => n.includes("kestrel")), names.join(", ")).toBe(true);
  });

  test("5.2 legacy knowledge_graph.json migrates on first start", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vg-it-legacy-"));
    const now = new Date().toISOString();
    const legacy = {
      sources: {
        src_a: { id: "src_a", doc_id: "doc_a", title: "Legacy", text: "Pollux Mining owns the Vega quarry.", created_at: now },
      },
      entities: {
        ent_1: { id: "ent_1", name: "Pollux Mining", type: "organization", description: "A mining company.", sources: ["src_a"] },
        ent_2: { id: "ent_2", name: "Vega Quarry", type: "location", description: "A quarry.", sources: ["src_a"] },
        ent_3: { id: "ent_3", name: "pollux mining", type: "organization", description: "Duplicate spelling.", sources: ["src_a"] },
      },
      relationships: {
        rel_1: { id: "rel_1", source: "ent_1", target: "ent_2", description: "Pollux Mining owns Vega Quarry.", sources: ["src_a"] },
      },
    };
    fs.writeFileSync(path.join(dir, "knowledge_graph.json"), JSON.stringify(legacy));
    const studio = await startStudio(8213, {}, dir);
    try {
      const g = await graph(await vg("viewer", studio.base));
      expect(g.nodes.map((n) => n.name).sort()).toEqual(["Pollux Mining", "Vega Quarry"]);
      expect(g.edges.length).toBe(1);
      const files = fs.readdirSync(dir);
      expect(files.some((f) => f.startsWith("knowledge_graph.json.migrated-")), files.join(", ")).toBe(true);
      expect(files).toContain("veritasgraph.db");
    } finally {
      await studio.stop();
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});
