import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config.
 *
 * Starts BOTH servers automatically:
 *   1. the FastAPI backend (via the repo virtualenv) on :8000
 *   2. the Next.js dev server on :3000 (which proxies /api -> :8000)
 *
 * Then runs the browser tests against http://127.0.0.1:3000.
 */
export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Backend: use the repo venv python; cwd is the app folder so `import app`
      // resolves. An isolated data dir keeps the demo graph/cases separate.
      // Port 8899 avoids clashing with other local services (8000/8010/8020 are taken).
      command:
        "../.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8899",
      cwd: "..",
      url: "http://127.0.0.1:8899/api/health",
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      env: { MUNI_DATA_DIR: "/tmp/muni-e2e-data", MUNI_CV_BACKEND: "sim" },
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:3000",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: { BACKEND_URL: "http://127.0.0.1:8899" },
    },
  ],
});
