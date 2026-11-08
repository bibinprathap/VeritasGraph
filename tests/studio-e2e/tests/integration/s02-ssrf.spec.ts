import { expect, test } from "@playwright/test";
import http from "node:http";
import { AddressInfo } from "node:net";
import { MODEL, Studio, startStudio, vg } from "./vg";

// C10 — tool probes refuse private/metadata networks unless explicitly allowed.
// Real targets: the local Ollama (loopback), OPA on the docker bridge (RFC1918).

const OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags";
const OPA_HEALTH = "http://172.17.0.1:8181/health";

async function probe(base: string, endpoint: string) {
  const api = await vg("editor", base);
  const created = await api.post("/tools", {
    data: { name: `probe ${Date.now()}`, config: { endpoint, method: "GET" } },
  });
  expect(created.status(), await created.text()).toBeLessThan(300);
  const id = (await created.json()).item.id;
  const r = await api.post(`/tools/${id}/test`);
  expect(r.status()).toBe(200);
  return r.json();
}

test.describe("S2 SSRF guard (C10)", () => {
  let allowPrivate: Studio;
  let allowAll: Studio;
  let redirector: http.Server;
  let redirectUrl = "";

  test.beforeAll(async () => {
    allowPrivate = await startStudio(8211, { STUDIO_TOOL_ALLOWED_NETWORKS: "127.0.0.1/32,172.17.0.0/16" });
    allowAll = await startStudio(8212, { STUDIO_TOOL_ALLOWED_NETWORKS: "0.0.0.0/0" });
    redirector = http.createServer((_req, res) => {
      res.writeHead(302, { Location: "http://169.254.169.254/latest/meta-data/" });
      res.end();
    });
    await new Promise<void>((r) => redirector.listen(0, "127.0.0.1", r));
    redirectUrl = `http://127.0.0.1:${(redirector.address() as AddressInfo).port}/`;
  });

  test.afterAll(async () => {
    await allowPrivate?.stop();
    await allowAll?.stop();
    redirector?.close();
  });

  for (const [name, url] of [
    ["2.1 loopback (real Ollama)", OLLAMA_TAGS],
    ["2.2 IPv4-mapped IPv6 loopback", "http://[::ffff:127.0.0.1]:11434/api/tags"],
    ["2.3 RFC1918 docker bridge (real OPA)", OPA_HEALTH],
    ["2.3b cloud metadata", "http://169.254.169.254/latest/meta-data/"],
  ] as const) {
    test(`${name} is refused by default`, async () => {
      const res = await probe(process.env.VG_BASE!, url);
      expect(res.ok).toBe(false);
      expect(res.detail).toMatch(/non-public address|Refusing/i);
    });
  }

  test("2.4 allowlisted loopback reaches the real Ollama", async () => {
    const res = await probe(allowPrivate.base, OLLAMA_TAGS);
    expect(res.ok, JSON.stringify(res)).toBe(true);
    expect(res.status_code).toBe(200);
    expect(JSON.stringify(res.sample)).toContain(MODEL.split(":")[0]);
  });

  test("2.5 allowlisted docker bridge reaches the real OPA", async () => {
    const res = await probe(allowPrivate.base, OPA_HEALTH);
    expect(res.ok, JSON.stringify(res)).toBe(true);
    expect(res.status_code).toBe(200);
  });

  test("2.6 metadata stays blocked even with 0.0.0.0/0", async () => {
    const res = await probe(allowAll.base, "http://169.254.169.254/latest/meta-data/");
    expect(res.ok).toBe(false);
    expect(res.detail).toMatch(/non-public address|Refusing/i);
  });

  test("2.7 redirects are not followed", async () => {
    const res = await probe(allowPrivate.base, redirectUrl);
    expect(res.status_code, JSON.stringify(res)).toBe(302);
  });
});
