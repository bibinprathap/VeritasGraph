import { APIRequestContext, expect, request as pwRequest, test } from "@playwright/test";
import { ChildProcess, spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const BASE = process.env.VG_BASE!;
export const MODEL = process.env.VG_MODEL!;
export const REPO_ROOT = process.env.VG_REPO_ROOT!;
export const PYTHON = process.env.VG_PYTHON!;
export const DATA_DIR = process.env.VG_DATA_DIR!;

export type Role = "viewer" | "editor" | "admin";

export const TOKENS: Record<Role, string> = {
  viewer: process.env.VG_VIEWER_TOKEN!,
  editor: process.env.VG_EDITOR_TOKEN!,
  admin: process.env.VG_ADMIN_TOKEN!,
};

export const tokenList = () =>
  (Object.keys(TOKENS) as Role[]).map((r) => `${TOKENS[r]}:${r}`).join(",");

/** An API context authenticated as ``role`` against ``base``. */
export async function vg(role: Role | null, base = BASE): Promise<APIRequestContext> {
  return pwRequest.newContext({
    baseURL: base,
    extraHTTPHeaders: role ? { Authorization: `Bearer ${TOKENS[role]}` } : {},
    timeout: 600_000,
  });
}

/** Mark a test BLOCKED (skipped with a reason) — never reported as passed. */
export function blocked(reason: string): void {
  test.info().annotations.push({ type: "blocked", description: reason });
  test.skip(true, `BLOCKED: ${reason}`);
}

export async function graph(api: APIRequestContext) {
  const r = await api.get("/graphrag/graph");
  expect(r.status()).toBe(200);
  return (await r.json()) as {
    nodes: { id: string; name: string; type: string; sources: string[] }[];
    edges: { id: string; source: string; target: string; predicate: string | null }[];
  };
}

export async function ingest(api: APIRequestContext, title: string, text: string) {
  const r = await api.post("/graphrag/ingest", { data: { title, text, model: MODEL } });
  expect(r.status(), await r.text()).toBe(200);
  return (await r.json()).result as { entities_added: number; relationships_added: number };
}

export async function ask(api: APIRequestContext, question: string, mode = "exploratory") {
  const r = await api.post("/graphrag/query", { data: { question, model: MODEL, mode } });
  expect(r.status(), await r.text()).toBe(200);
  return r.json();
}

// --------------------------------------------------------------------------- //
// Extra Studio instances (different env, e.g. SSRF allowlists or migration)
// --------------------------------------------------------------------------- //
export type Studio = { base: string; dataDir: string; proc: ChildProcess; stop: () => Promise<void> };

export async function startStudio(port: number, env: Record<string, string>, dataDir?: string): Promise<Studio> {
  const ownsDataDir = dataDir === undefined;
  const dir = dataDir ?? fs.mkdtempSync(path.join(os.tmpdir(), "vg-it-extra-"));
  const proc = spawn(
    PYTHON,
    ["-m", "uvicorn", "studio_api.main:app", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"],
    {
      cwd: REPO_ROOT,
      env: {
        ...process.env,
        STUDIO_DATA_DIR: dir,
        STUDIO_API_TOKENS: tokenList(),
        STUDIO_AUTH: "",
        VERITASGRAPH_DB: "",
        ...env,
      },
      stdio: ["ignore", "ignore", "pipe"],
    },
  );
  let stderr = "";
  proc.stderr?.on("data", (d) => (stderr += d.toString()));
  const base = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) throw new Error(`Studio on :${port} exited: ${stderr.slice(-2000)}`);
    try {
      const r = await fetch(`${base}/health`);
      if (r.ok) break;
    } catch {
      /* not up yet */
    }
    await new Promise((res) => setTimeout(res, 300));
  }
  const stop = async () => {
    if (proc.exitCode === null) {
      proc.kill("SIGTERM");
      await new Promise((res) => proc.once("exit", res));
    }
    if (ownsDataDir) fs.rmSync(dir, { recursive: true, force: true });
  };
  return { base, dataDir: dir, proc, stop };
}

// --------------------------------------------------------------------------- //
// VeritasGraph MCP over stdio
// --------------------------------------------------------------------------- //
export type RpcReq = { method: string; params?: Record<string, unknown> };

function mcpEnv(mode: string | null, dataDir: string) {
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    STUDIO_DATA_DIR: dataDir,
    VERITASGRAPH_DB: "",
    VERITASGRAPH_MODEL: MODEL,
  };
  if (mode === null) delete env.VERITASGRAPH_MCP_MODE;
  else env.VERITASGRAPH_MCP_MODE = mode;
  return env;
}

function frame(reqs: RpcReq[]) {
  return reqs.map((r, i) => JSON.stringify({ jsonrpc: "2.0", id: i + 1, ...r })).join("\n") + "\n";
}

function parse(stdout: string) {
  return stdout
    .split("\n")
    .filter((l) => l.trim().startsWith("{"))
    .map((l) => JSON.parse(l));
}

/** Run one MCP session synchronously; returns the JSON-RPC responses in order. */
export function mcp(mode: string | null, reqs: RpcReq[], dataDir = DATA_DIR) {
  const p = spawnSync(PYTHON, ["-m", "veritasgraph_mcp"], {
    cwd: REPO_ROOT,
    env: mcpEnv(mode, dataDir),
    input: frame(reqs),
    encoding: "utf8",
    timeout: 600_000,
  });
  return { status: p.status, stderr: p.stderr, responses: parse(p.stdout) };
}

/** Same as {@link mcp} but non-blocking, for concurrency tests. */
export function mcpAsync(mode: string | null, reqs: RpcReq[], dataDir = DATA_DIR) {
  return new Promise<{ status: number | null; stderr: string; responses: any[] }>((resolve) => {
    const p = spawn(PYTHON, ["-m", "veritasgraph_mcp"], { cwd: REPO_ROOT, env: mcpEnv(mode, dataDir) });
    let out = "";
    let err = "";
    p.stdout.on("data", (d) => (out += d.toString()));
    p.stderr.on("data", (d) => (err += d.toString()));
    p.on("exit", (code) => resolve({ status: code, stderr: err, responses: parse(out) }));
    p.stdin.end(frame(reqs));
  });
}

export const toolResult = (resp: any) => JSON.parse(resp.result.content[0].text);
