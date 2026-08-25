import { test, expect } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

test.describe("Check 8.7: Throughput Measurement Mode & Replay Label", () => {
  test("measurement mode rendered; a replay fixture renders a 'not a performance claim' label", async ({
    page,
  }) => {
    // 1. Test replay mode fixture
    const replayFixture = {
      ...seed5Fixture,
      throughput: {
        ...seed5Fixture.throughput,
        measurement_mode: "replay",
      },
    };

    await page.route("**/rest/v1/runs*", async (route) => {
      const runRow = {
        run_id: replayFixture.run_id,
        engine_version: replayFixture.engine_version,
        status: "complete",
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        report: replayFixture,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([runRow]),
      });
    });

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Run Dashboard" })).toBeVisible();

    // Verify Throughput card badge renders 'replay'
    const throughputCard = page.locator("div.panel", { hasText: "Throughput" });
    await expect(throughputCard.getByText("replay", { exact: true })).toBeVisible();

    // Verify note renders 'not a performance claim'
    await expect(throughputCard.getByText(/not a performance claim/i)).toBeVisible();
  });

  test("live mode fixture renders live measurement mode note", async ({ page }) => {
    // 2. Test live mode fixture
    const liveFixture = {
      ...seed5Fixture,
      throughput: {
        ...seed5Fixture.throughput,
        measurement_mode: "live",
      },
    };

    await page.route("**/rest/v1/runs*", async (route) => {
      const runRow = {
        run_id: liveFixture.run_id,
        engine_version: liveFixture.engine_version,
        status: "complete",
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        report: liveFixture,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([runRow]),
      });
    });

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Run Dashboard" })).toBeVisible();

    const throughputCard = page.locator("div.panel", { hasText: "Throughput" });
    await expect(throughputCard.getByText("live", { exact: true })).toBeVisible();
    await expect(throughputCard.getByText(/Measurement mode: live over/i)).toBeVisible();
  });
});
