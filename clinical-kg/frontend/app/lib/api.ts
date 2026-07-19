// Thin API client. Requests go through Next.js rewrites at /api/* -> backend.

export type Assertion = {
  system: string;
  code: string;
  display: string;
  label: string;
  negation: string;
  certainty: string;
  temporality: string;
  experiencer: string;
  contradiction: boolean;
  attributes: Record<string, unknown>;
  citations: string[];
  conflicting_spans: { section: string; text: string; citation: string }[];
};

export type Match = {
  patient_id: string;
  reasons: string[];
  citations: string[];
};

export type Fact = {
  ntype: string;
  display: string;
  negation: string;
  certainty: string;
  temporality: string;
  experiencer: string;
  contradiction: boolean;
  citations: string[];
  [k: string]: unknown;
};

export type GraphData = {
  nodes: { data: { id: string; label: string; ntype: string } }[];
  edges: { data: { source: string; target: string; rel: string } }[];
};

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => j<{ status: string; stats: any }>("/api/health"),
  loadSamples: () =>
    j<{ loaded: number; stats: any }>("/api/demo/load-samples", {
      method: "POST",
    }),
  reset: () => j("/api/reset", { method: "POST" }),
  ingest: (notes: any[]) =>
    j<{ ingested: any[]; stats: any }>("/api/ingest", {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),
  query: (query: string) =>
    j<{
      query: string;
      parsed: any;
      match_count: number;
      matches: Match[];
    }>("/api/query", { method: "POST", body: JSON.stringify({ query }) }),
  patients: () =>
    j<{ patients: { patient_id: string; facts: Fact[] }[] }>("/api/patients"),
  contradictions: () =>
    j<{ contradictions: (Assertion & { patient_id: string; doc_id: string })[] }>(
      "/api/contradictions"
    ),
  graph: (patientId?: string) =>
    j<GraphData>(
      "/api/graph" + (patientId ? `?patient_id=${patientId}` : "")
    ),
  kAnonymity: (records: any[], quasi: string[], targetK: number) =>
    j<any>("/api/risk/k-anonymity", {
      method: "POST",
      body: JSON.stringify({
        records,
        quasi_identifiers: quasi,
        target_k: targetK,
      }),
    }),
};
