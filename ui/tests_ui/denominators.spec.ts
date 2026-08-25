import { test, expect } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

const integer = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const count = (n: number): string => integer.format(n);

test.describe("Check 8.2: Rate Denominators & Provenance", () => {
  test("every rate shows numerator AND denominator; seed and seed-set visible", async ({
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

    // 1. Seed and Seed-set visible in the header badge
    await expect(page.getByText("Seed", { exact: true })).toBeVisible();
    await expect(page.getByText(count(seed5Fixture.config.seed), { exact: true })).toBeVisible();
    await expect(page.getByText("Seed set", { exact: true })).toBeVisible();
    await expect(page.getByText(seed5Fixture.config.seed_set, { exact: true })).toBeVisible();

    // 2. Match rate shows percentage and explicit numerator / denominator
    const matchRatePercent = `${(seed5Fixture.accuracy.match_rate.value * 100).toFixed(2)}%`;
    const matchRateNumDen = `${count(seed5Fixture.accuracy.match_rate.numerator)} / ${count(seed5Fixture.accuracy.match_rate.denominator)} in-scope items`;
    await expect(page.getByRole("status").filter({ hasText: matchRatePercent })).toBeVisible();
    await expect(page.getByText(matchRateNumDen, { exact: false })).toBeVisible();

    // 3. Resolved rate shows percentage and explicit numerator / denominator
    const resolvedRatePercent = `${(seed5Fixture.accuracy.resolved_rate.value * 100).toFixed(2)}%`;
    const resolvedRateNumDen = `${count(seed5Fixture.accuracy.resolved_rate.numerator)} / ${count(seed5Fixture.accuracy.resolved_rate.denominator)} matched groups`;
    await expect(page.getByRole("status").filter({ hasText: resolvedRatePercent })).toBeVisible();
    await expect(page.getByText(resolvedRateNumDen, { exact: false })).toBeVisible();

    // 4. Unresolved tile shows explicit numerator / denominator
    const unresolvedNumDen = `${count(seed5Fixture.accuracy.unresolved_rate.numerator)} / ${count(seed5Fixture.accuracy.unresolved_rate.denominator)} in-scope items`;
    await expect(page.getByText(unresolvedNumDen, { exact: false })).toBeVisible();

    // 5. Throughput shows explicit numerator / denominator (rows / s)
    const throughputNumDen = `${count(seed5Fixture.throughput.rows_per_second_end_to_end.numerator)} rows / ${count(seed5Fixture.throughput.rows_per_second_end_to_end.denominator)} s end-to-end`;
    await expect(page.getByText(throughputNumDen, { exact: false })).toBeVisible();

    // 6. Blocker recall shows numerator / denominator
    const blockerNumDen = `${count(seed5Fixture.candidate_space.blocker_recall.numerator)} / ${count(seed5Fixture.candidate_space.blocker_recall.denominator)} true pairs retained`;
    await expect(page.getByText(blockerNumDen, { exact: false })).toBeVisible();

    // 7. Agent lift in ablation panel shows numerator / denominator
    const liftNumDen = `${count(seed5Fixture.ablation.agent_lift.numerator)} / ${count(seed5Fixture.ablation.agent_lift.denominator)} residuals recovered by the agent path`;
    await expect(page.getByText(liftNumDen, { exact: false })).toBeVisible();
  });
});
