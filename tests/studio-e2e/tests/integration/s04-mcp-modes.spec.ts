import { expect, test } from "@playwright/test";
import { MODEL, graph, ingest, mcp, toolResult, vg } from "./vg";

// C8, C9, C11 — MCP mode gating, and MCP writes visible to Studio (shared store).

const READ_TOOLS = [
  "check_answerable", "query", "search_entities", "get_entity", "get_graph",
  "get_ontology", "search_terms", "get_term", "get_answer_receipt", "compile_status",
  "structured_search", "structured_get_term", "structured_list_measures", "structured_ask",
].map((t) => `veritasgraph_${t}`);

const listTools = (mode: string | null) => {
  const r = mcp(mode, [{ method: "initialize", params: {} }, { method: "tools/list" }]);
  expect(r.status, r.stderr).toBe(0);
  return (r.responses[1].result.tools as { name: string }[]).map((t) => t.name).sort();
};

test.describe("S4 MCP modes (C8, C9, C11)", () => {
  test.beforeAll(async () => {
    expect((await (await vg("admin")).delete("/graphrag/graph")).status()).toBe(200);
    await ingest(await vg("editor"), "S4 seed", "Marlow Systems builds payroll software in Leeds.");
  });

  test("4.1 read mode lists only read tools and refuses clear_graph", async () => {
    expect(listTools("read")).toEqual([...READ_TOOLS].sort());
    const before = (await graph(await vg("viewer"))).nodes.length;
    const r = mcp("read", [
      { method: "initialize", params: {} },
      { method: "tools/call", params: { name: "veritasgraph_clear_graph", arguments: {} } },
    ]);
    expect(r.responses[1].error?.code).toBe(-32601);
    expect((await graph(await vg("viewer"))).nodes.length).toBe(before);
  });

  test("4.2 default mode is write: ingest yes, clear no", async () => {
    const tools = listTools(null);
    expect(tools).toContain("veritasgraph_ingest_document");
    expect(tools).toContain("veritasgraph_propose_term");
    expect(tools).not.toContain("veritasgraph_clear_graph");
  });

  test("4.3 MCP ingest is visible through Studio (shared SQLite store)", async () => {
    const r = mcp("write", [
      { method: "initialize", params: {} },
      {
        method: "tools/call",
        params: {
          name: "veritasgraph_ingest_document",
          arguments: { title: "MCP doc", text: "Halvard Shipping operates container vessels out of Bergen.", model: MODEL },
        },
      },
    ]);
    expect(r.responses[1].error, r.stderr).toBeUndefined();
    expect(r.responses[1].result.isError, r.responses[1].result.content?.[0]?.text).toBeFalsy();
    const names = (await graph(await vg("viewer"))).nodes.map((n) => n.name.toLowerCase());
    expect(names.some((n) => n.includes("halvard"))).toBe(true);
  });

  test("4.4 admin mode can clear; Studio sees the empty graph", async () => {
    expect(listTools("admin")).toContain("veritasgraph_clear_graph");
    const r = mcp("admin", [
      { method: "initialize", params: {} },
      { method: "tools/call", params: { name: "veritasgraph_clear_graph", arguments: {} } },
    ]);
    expect(r.responses[1].error, r.stderr).toBeUndefined();
    expect(r.responses[1].result.isError).toBeFalsy();
    expect((await graph(await vg("viewer"))).nodes.length).toBe(0);
  });

  test("4.5 an unknown mode fails closed to read", async () => {
    expect(listTools("bogus")).toEqual([...READ_TOOLS].sort());
  });

  test("4.6 initialize instructions point agents at check_answerable", async () => {
    const r = mcp("read", [{ method: "initialize", params: {} }]);
    expect(JSON.stringify(r.responses[0].result.instructions ?? "")).toMatch(/check_answerable/);
  });

  test("4.7 read-mode get_graph returns the same graph as Studio", async () => {
    await ingest(await vg("editor"), "S4 seed 2", "Marlow Systems builds payroll software in Leeds.");
    const r = mcp("read", [
      { method: "initialize", params: {} },
      { method: "tools/call", params: { name: "veritasgraph_get_graph", arguments: {} } },
    ]);
    const viaMcp = toolResult(r.responses[1]);
    expect((viaMcp.nodes ?? []).length).toBe((await graph(await vg("viewer"))).nodes.length);
  });
});
