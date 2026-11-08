import { defineConfig, devices } from "@playwright/test";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Real-integration suite for VERITASGRAPH_PLAYWRIGHT_INTEGRATION_TESTS.md.
 *
 * Starts a fresh, authenticated Studio on :8210 with a throwaway data dir and
 * random per-run tokens, backed by the local Ollama. No mocks.
 *
 *   npx playwright test -c playwright.integration.config.ts
 */
const here = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(here, "../..");
const token = () => crypto.randomBytes(24).toString("hex");
const ownsDataDir = !process.env.VG_DATA_DIR;

// Values set here are inherited by the worker processes, so they stay stable.
process.env.VG_VIEWER_TOKEN ||= token();
process.env.VG_EDITOR_TOKEN ||= token();
process.env.VG_ADMIN_TOKEN ||= token();
process.env.VG_DATA_DIR ||= fs.mkdtempSync(path.join(os.tmpdir(), "vg-it-"));
process.env.VG_DATA_DIR_AUTO ||= ownsDataDir ? "1" : "0";
process.env.VG_PORT ||= "8210";
process.env.VG_BASE ||= `http://127.0.0.1:${process.env.VG_PORT}`;
process.env.STUDIO_URL ||= `${process.env.VG_BASE}/studio`;
process.env.VG_MODEL ||= "llama3.1:8b";
process.env.VG_REPO_ROOT ||= REPO_ROOT;
process.env.VG_PYTHON ||= path.join(REPO_ROOT, ".venv/bin/python");
process.env.OLLAMA_HOST ||= "127.0.0.1:11434";

export const studioTokens = () =>
  [
    `${process.env.VG_VIEWER_TOKEN}:viewer`,
    `${process.env.VG_EDITOR_TOKEN}:editor`,
    `${process.env.VG_ADMIN_TOKEN}:admin`,
  ].join(",");

export default defineConfig({
  testDir: "./tests/integration",
  testMatch: /s\d\d-.*\.spec\.ts/,
  timeout: 600_000,
  expect: { timeout: 60_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  globalTeardown: "./integration.teardown.ts",
  reporter: [["list"], ["json", { outputFile: "test-results/integration.json" }]],
  use: {
    baseURL: process.env.VG_BASE,
    headless: true,
    actionTimeout: 30_000,
    trace: "off", // traces would record bearer tokens
    screenshot: "only-on-failure",
  },
  projects: [{ name: "integration", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `${process.env.VG_PYTHON} -m uvicorn studio_api.main:app --host 127.0.0.1 --port ${process.env.VG_PORT} --log-level warning`,
    cwd: REPO_ROOT,
    url: `${process.env.VG_BASE}/health`,
    reuseExistingServer: false,
    timeout: 90_000,
    env: {
      STUDIO_DATA_DIR: process.env.VG_DATA_DIR!,
      STUDIO_API_TOKENS: studioTokens(),
      STUDIO_AUTH: "",
      STUDIO_TOOL_ALLOWED_NETWORKS: "",
      STUDIO_CORS_ORIGINS: "",
      VERITASGRAPH_DB: "",
      OLLAMA_HOST: process.env.OLLAMA_HOST!,
    },
  },
});
