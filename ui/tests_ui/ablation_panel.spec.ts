import { test, expect } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

const integer = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const count = (n: number): string => integer.format(n);

test.describe("Check 8.4: Four-Arm Ablation Panel", () => {
  test("all 4 ablation arms render; agent_lift and precision_cost both visible", async ({
    page,
  }) => {
    // Intercept runs query to deterministically supply seed5 fixture
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

    // 1. Ablation Panel Section Heading
    await expect(
      page.getByRole("heading", { name: "Baselines — four ablation arms" }),
    ).toBeVisible();

    // 2. All 4 ablation arms render in the table
    const table = page.locator("table");
    await expect(table.getByText("rules only", { exact: true })).toBeVisible();
    await expect(table.getByText("agent only", { exact: true })).toBeVisible();
    await expect(table.getByText("rules + agent", { exact: true })).toBeVisible();
    await expect(table.getByText("random", { exact: true })).toBeVisible();

    // Verify rules_only match rate
    const rulesMatchRate = `${(seed5Fixture.ablation.rules_only.match_rate * 100).toFixed(2)}%`;
    await expect(table.getByText(rulesMatchRate)).toBeVisible();

    // Verify rules_agent match rate
    const hybridMatchRate = `${(seed5Fixture.ablation.rules_agent.match_rate * 100).toFixed(2)}%`;
    await expect(table.getByText(hybridMatchRate)).toBeVisible();

    // 3. Agent Lift tile visible with percentage and numerator/denominator
    const liftCard = page.locator("div.panel", { hasText: "Agent lift" });
    await expect(liftCard).toBeVisible();
    const liftPercent = `${(seed5Fixture.ablation.agent_lift.value * 100).toFixed(2)}%`;
    await expect(liftCard.getByText(liftPercent, { exact: true })).toBeVisible();
    const liftLine = `${count(seed5Fixture.ablation.agent_lift.numerator)} / ${count(seed5Fixture.ablation.agent_lift.denominator)} residuals recovered by the agent path`;
    await expect(liftCard.getByText(liftLine, { exact: false })).toBeVisible();

    // 4. Precision Cost tile visible with percentage
    const costCard = page.locator("div.panel", { hasText: "Precision cost" });
    await expect(costCard).toBeVisible();
    const costPercent = `${(seed5Fixture.ablation.precision_cost * 100).toFixed(2)}%`;
    await expect(costCard.getByText(costPercent, { exact: true })).toBeVisible();
  });
});
