import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.FLOORPLAN_PORT ?? 3100);
const baseURL = process.env.FLOORPLAN_BASE_URL ?? `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./tests/e2e",
  // Extraction shells out to Python; an 8-sheet set takes a few seconds and
  // the first run also pays Next's on-demand compile.
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  globalSetup: "./tests/e2e/global-setup.ts",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 20_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.FLOORPLAN_BASE_URL
    ? undefined
    : {
        command: `npm run start -- -p ${PORT}`,
        url: `${baseURL}/api/samples`,
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
        stdout: "pipe",
        stderr: "pipe",
      },
});
