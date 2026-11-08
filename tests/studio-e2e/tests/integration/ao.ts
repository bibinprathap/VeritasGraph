import { APIRequestContext, request as pwRequest, test } from "@playwright/test";

// Auto-Ontology access for S7-S10. Every AO test is gated: if AO, its API token,
// or an engine is not actually available, the test is BLOCKED (skipped with a
// reason), never passed.

export const AO_URL = process.env.AO_URL ?? "";
export const AO_API_TOKEN = process.env.AO_API_TOKEN ?? "";
export const AO_VIEWER_TOKEN = process.env.AO_VIEWER_API_TOKEN ?? "";

export const ENGINES = [
  { key: "postgresql", db: "sales_pg", product: "Probe Widget PG", golden: 588.8, env: "AO_SRC_POSTGRESQL", ui: true },
  { key: "mysql", db: "sales_my", product: "Probe Widget MY", golden: 412.5, env: "AO_SRC_MYSQL", ui: true },
  { key: "databricks", db: "sales_dbx", product: "Probe Widget DBX", golden: 1024.0, env: "DATABRICKS_URL", ui: true },
  { key: "snowflake", db: "SALES_SF", product: "Probe Widget SF", golden: 77.25, env: "SNOWFLAKE_URL", ui: true },
  { key: "clickhouse", db: "sales_ch", product: "Probe Widget CH", golden: 300.0, env: "AO_SRC_CLICKHOUSE", ui: true },
  { key: "trino", db: "sales_tr", product: "Probe Widget TR", golden: 950.4, env: "AO_SRC_TRINO", ui: true },
  { key: "kyuubi", db: "sales_ky", product: "Probe Widget KY", golden: 128.64, env: "KYUUBI_URL", ui: true },
  { key: "heavydb", db: "sales_hv", product: "Probe Widget HV", golden: 640.0, env: "AO_SRC_HEAVYDB", ui: true },
  { key: "duckdb", db: "sales_dd", product: "Probe Widget DD", golden: 215.1, env: "AO_SRC_DUCKDB", ui: false },
  { key: "sqlite", db: "sales_sl", product: "Probe Widget SL", golden: 49.99, env: "AO_SRC_SQLITE", ui: false },
] as const;

let probed: string | null | undefined;

/** Why AO cannot be used right now, or null when it is reachable and authenticated. */
export async function aoUnavailable(): Promise<string | null> {
  if (probed !== undefined) return probed;
  if (!AO_URL) return (probed = "AO_URL unset — Auto-Ontology is not deployed for this run");
  if (!AO_API_TOKEN) return (probed = "AO_API_TOKEN unset — mint one under User menu → API Tokens");
  try {
    const r = await fetch(`${AO_URL}/api/health`, { signal: AbortSignal.timeout(5_000) });
    if (!r.ok) return (probed = `AO /api/health returned ${r.status}`);
  } catch (e) {
    return (probed = `AO unreachable at ${AO_URL}: ${(e as Error).message}`);
  }
  return (probed = null);
}

export async function blockedUnlessAo(extra?: string | null): Promise<void> {
  const reason = (await aoUnavailable()) ?? extra ?? null;
  if (reason) {
    test.info().annotations.push({ type: "blocked", description: reason });
    test.skip(true, `BLOCKED: ${reason}`);
  }
}

export async function ao(token = AO_API_TOKEN): Promise<APIRequestContext> {
  return pwRequest.newContext({ baseURL: AO_URL, extraHTTPHeaders: { "x-api-key": token }, timeout: 900_000 });
}

export type AoEvent = { type: string; node?: string; phase?: string; answer?: any; message?: string };

/** POST /api/chat/completions and collect the SSE events. */
export async function aoAsk(api: APIRequestContext, question: string): Promise<AoEvent[]> {
  const res = await api.post("/api/chat/completions", { data: { question } });
  if (!res.ok()) throw new Error(`chat/completions -> ${res.status()}: ${await res.text()}`);
  const events: AoEvent[] = [];
  for (const line of (await res.text()).split("\n")) {
    if (!line.startsWith("data:")) continue;
    const payload = line.slice(5).trim();
    if (payload === "[DONE]") break;
    events.push(JSON.parse(payload));
  }
  return events;
}

export const aoResult = (ev: AoEvent[]) => ev.find((e) => e.type === "result")?.answer;
export const aoNodes = (ev: AoEvent[]) => new Set(ev.filter((e) => e.type === "step").map((e) => e.node));
