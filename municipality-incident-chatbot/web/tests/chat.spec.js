import { test, expect } from "@playwright/test";
import path from "path";
import os from "os";
import fs from "fs";

// Helper: create a temp fake photo with a given name. The offline CV backend
// infers the detected object from the file name.
function tempPhoto(name) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "muni-pw-"));
  const p = path.join(dir, name);
  fs.writeFileSync(p, Buffer.from([0xff, 0xd8, 0xff, 0xe0]));
  return p;
}

// A real photo of an abandoned vehicle checked into the repo. The offline CV
// backend infers "car" from the file name ("...cars...").
const REAL_ABANDONED_VEHICLE = path.join(
  __dirname,
  "..",
  "..",
  "tests",
  "abandoned-cars-dubai-032220220211-1024x640.jpg"
);

test.beforeEach(async ({ page }) => {
  // Isolate each test: clear previously registered cases so duplicate
  // detection and counts are deterministic across runs.
  await page.request.post("/api/reset");
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Department of Municipality/i })).toBeVisible();
});

test("loads and shows the VeritasGraph knowledge-graph stats", async ({ page }) => {
  await expect(page.getByText(/VeritasGraph/)).toBeVisible();
  await expect(page.getByText(/knowledge graph: \d+ nodes/)).toBeVisible();
});

test("auto-validates a trash report with photo + corroborated location", async ({ page }) => {
  await page.getByTestId("message-input").fill("the trash is overflowing near the market");
  await page.getByTestId("zone-select").selectOption("downtown");
  await page.getByTestId("file-input").setInputFiles(tempPhoto("garbage_overflow.jpg"));
  await page.getByTestId("send-btn").click();

  const badge = page.getByTestId("outcome-badge");
  await expect(badge).toHaveText("AUTO_VALIDATED");
  await expect(page.getByTestId("case-id")).toContainText("MUN-");
  await expect(page.getByTestId("case-id")).toContainText("Sanitation Department");
  // The case appears in the cases list.
  await expect(page.getByTestId("cases-list")).toContainText("MUN-");
});

test("needs review when location has no corroboration", async ({ page }) => {
  await page.getByTestId("message-input").fill("trash overflowing here");
  await page.getByTestId("zone-select").selectOption("far-suburb");
  await page.getByTestId("file-input").setInputFiles(tempPhoto("garbage_overflow.jpg"));
  await page.getByTestId("send-btn").click();

  await expect(page.getByTestId("outcome-badge")).toHaveText("NEEDS_REVIEW");
});

test("rejects a report with no photo evidence", async ({ page }) => {
  await page.getByTestId("message-input").fill("trash overflowing here");
  await page.getByTestId("zone-select").selectOption("far-suburb");
  await page.getByTestId("send-btn").click();

  await expect(page.getByTestId("outcome-badge")).toHaveText("REJECTED");
});

test("out-of-scope message is rejected without a category", async ({ page }) => {
  await page.getByTestId("sample-3").click(); // "Out of scope" quick scenario
  await expect(page.getByTestId("outcome-badge")).toHaveText("REJECTED");
});

test("quick scenario: illegal parking routes to Traffic Police", async ({ page }) => {
  await page.getByTestId("sample-1").click(); // Illegal parking (downtown)
  await expect(page.getByTestId("case-id")).toContainText("Traffic Police");
});

test("duplicate report is detected and rejected", async ({ page }) => {
  // First report (downtown, auto-validated).
  await page.getByTestId("message-input").fill("the trash is overflowing near the market");
  await page.getByTestId("zone-select").selectOption("downtown");
  await page.getByTestId("file-input").setInputFiles(tempPhoto("garbage_overflow.jpg"));
  await page.getByTestId("send-btn").click();
  await expect(page.getByTestId("outcome-badge").first()).toBeVisible();

  // Second identical report at the same location -> duplicate.
  await page.getByTestId("message-input").fill("garbage still overflowing here");
  await page.getByTestId("zone-select").selectOption("downtown");
  await page.getByTestId("file-input").setInputFiles(tempPhoto("garbage_overflow.jpg"));
  await page.getByTestId("send-btn").click();

  await expect(page.getByTestId("chat")).toContainText(/duplicate/i);
});

test("captures reporter details and a free-text location", async ({ page }) => {
  await page.getByTestId("message-input").fill("the trash is overflowing near the market");
  await page.getByTestId("zone-select").selectOption("downtown");
  await page.getByTestId("location-input").fill("12 Market Street, near the bus stop");
  await page.getByTestId("name-input").fill("Aisha Khan");
  await page.getByTestId("phone-input").fill("+971500000000");
  await page.getByTestId("file-input").setInputFiles(tempPhoto("garbage_overflow.jpg"));
  await page.getByTestId("send-btn").click();

  await expect(page.getByTestId("outcome-badge")).toHaveText("AUTO_VALIDATED");
  // The bot acknowledges the reporter by name.
  await expect(page.getByTestId("chat")).toContainText(/Thanks Aisha Khan/);
  // The case card shows the reporter and the free-text location.
  const cases = page.getByTestId("cases-list");
  await expect(cases).toContainText("Aisha Khan");
  await expect(cases).toContainText("12 Market Street");
});

test("use-my-location button captures GPS coordinates", async ({ page, context }) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 25.276987, longitude: 55.296249 });

  await page.getByTestId("message-input").fill("a car is parked illegally blocking the road");
  await page.getByTestId("zone-select").selectOption("");
  await page.getByTestId("geo-btn").click();
  await expect(page.getByTestId("geo-status")).toContainText("25.276987");

  await page.getByTestId("file-input").setInputFiles(tempPhoto("car_blocking.jpg"));
  await page.getByTestId("send-btn").click();

  await expect(page.getByTestId("outcome-badge")).toBeVisible();
  await expect(page.getByTestId("cases-list")).toContainText("25.276987");
});

test("real abandoned-vehicle photo -> Transport Department, needs review", async ({ page }) => {
  await page.getByTestId("message-input").fill("there is an abandoned vehicle near my home");
  await page.getByTestId("zone-select").selectOption("downtown");
  await page.getByTestId("location-input").fill("behind the auto workshop, Al Ain St");
  await page.getByTestId("name-input").fill("Sara Ali");
  await page.getByTestId("phone-input").fill("+971500000000");
  await page.getByTestId("file-input").setInputFiles(REAL_ABANDONED_VEHICLE);
  await page.getByTestId("send-btn").click();

  // Abandoned vehicle with a photo but no CCTV/sensor corroboration -> review.
  await expect(page.getByTestId("outcome-badge")).toHaveText("NEEDS_REVIEW");
  await expect(page.getByTestId("case-id")).toContainText("Transport Department");
  await expect(page.getByTestId("chat")).toContainText(/Thanks Sara Ali/);
  const cases = page.getByTestId("cases-list");
  await expect(cases).toContainText("Sara Ali");
  await expect(cases).toContainText("behind the auto workshop");
});
