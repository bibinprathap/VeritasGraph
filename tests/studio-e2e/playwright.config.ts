import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the live VeritasGraph Studio demo.
 *
 * The default target is the public GitHub Pages entry point, which performs a
 * meta-refresh redirect to the live Cloudflare-tunnelled Studio. Override with:
 *
 *   STUDIO_URL=http://127.0.0.1:8200/studio npx playwright test   # local backend
 *   STUDIO_URL=https://<your-tunnel>/studio  npx playwright test   # a specific tunnel
 *
 * Set RUN_WRITE_TESTS=1 to also run the tests that create/delete an agent
 * (skipped by default so we never pollute the shared live demo).
 */
const STUDIO_URL =
  process.env.STUDIO_URL || "https://bibinprathap.github.io/VeritasGraph/studio/";

export default defineConfig({
  testDir: "./tests",
  // The live demo goes over a Cloudflare tunnel with a hard 100s edge timeout,
  // so keep per-test and per-assertion timeouts generous.
  timeout: 120_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: STUDIO_URL,
    headless: true,
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
    ignoreHTTPSErrors: true,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
