import { test, expect } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

test.describe("Check 10.7: Falsification Statement on Verify Page", () => {
  test("all 6 conditions from IMPLEMENTATION_PLAN.md §4.10 render on the Verify page", async ({
    page,
  }) => {
    // Intercept runs query
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

    // Intercept other tables with empty arrays so page renders
    await page.route("**/rest/v1/agent_calls*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/rest/v1/control_results*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/rest/v1/closures*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/rest/v1/exceptions*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/verify");
    await expect(page.getByRole("heading", { name: "Verify" })).toBeVisible();

    // 1. Verify Falsification statement section
    await expect(page.getByRole("heading", { name: "Falsification statement" })).toBeVisible();

    const falsificationSection = page.locator("section", {
      has: page.getByRole("heading", { name: "Falsification statement" }),
    });

    // 2. All 6 falsifier conditions rendered in order (1-6)
    const listItems = falsificationSection.locator("ol > li");
    await expect(listItems).toHaveCount(6);

    // Condition 1: Holdout minimum
    await expect(
      listItems.nth(0).getByText(/match_rate on a fresh unseen seed falls below/i),
    ).toBeVisible();

    // Condition 2: Negative controls
    await expect(listItems.nth(1).getByText(/negative control/i)).toBeVisible();

    // Condition 3: Truth leak in prompt
    await expect(listItems.nth(2).getByText(/truth label is found in any prompt/i)).toBeVisible();

    // Condition 4: Blocker recall
    await expect(listItems.nth(3).getByText(/blocker_recall < 1\.0/i)).toBeVisible();

    // Condition 5: Reconciliation of exception list
    await expect(listItems.nth(4).getByText(/resolved \+ unresolved != rows_total/i)).toBeVisible();

    // Condition 6: Closure on open exception
    await expect(
      listItems.nth(5).getByText(/closure exists for a row in an open exception/i),
    ).toBeVisible();
  });
});
