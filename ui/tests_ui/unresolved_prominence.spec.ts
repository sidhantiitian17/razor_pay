import { test, expect } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

test.describe("Check 8.5: Unresolved Tile Prominence", () => {
  test("unresolved tile visible in the initial 1440px viewport; font-size >= match-rate tile's", async ({
    page,
  }) => {
    // Set explicit desktop viewport (1440x900)
    await page.setViewportSize({ width: 1440, height: 900 });

    await page.route("**/rest/v1/runs*", async (route) => {
      const runRow = {
        run_id: seed5Fixture.run_id,
        engine_version: seed5Fixture.engine_version,
        status: "complete",
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        report: seed5Fixture,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([runRow]),
      });
    });

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Run Dashboard" })).toBeVisible();

    // 1. Locate Unresolved stat card and Match rate rate card
    const unresolvedCard = page
      .locator("div.panel")
      .filter({ has: page.getByText("Unresolved", { exact: true }) })
      .first();
    await expect(unresolvedCard).toBeVisible();

    const matchRateCard = page
      .locator("div.panel")
      .filter({ has: page.getByText("Match rate", { exact: true }) })
      .first();
    await expect(matchRateCard).toBeVisible();

    // 2. Assert Unresolved card is within initial viewport
    const box = await unresolvedCard.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(900);

    // 3. Compare computed font sizes of the primary numeric readouts
    const unresolvedValueEl = unresolvedCard.locator(".tnum.font-semibold");
    const matchRateValueEl = matchRateCard.locator(".tnum.font-semibold");

    const unresolvedFontSize = await unresolvedValueEl.evaluate((el) => {
      return parseFloat(window.getComputedStyle(el).fontSize);
    });
    const matchRateFontSize = await matchRateValueEl.evaluate((el) => {
      return parseFloat(window.getComputedStyle(el).fontSize);
    });

    // Unresolved font size must be >= Match rate font size (both text-3xl = 30px)
    expect(unresolvedFontSize).toBeGreaterThanOrEqual(matchRateFontSize);
  });
});
