import { test, expect } from "@playwright/test";
import { setupEvalLabMocks } from "./mock_eval_sweeps";

test.describe("Worst Seed Gate (Check 11.2, R10)", () => {
  test("highlighted worst seed equals min(match_rate) and is labelled as the gate", async ({
    page,
  }) => {
    // Intercept Supabase endpoints to provide real 20-seed holdout sweep fixture
    await setupEvalLabMocks(page);

    await page.goto("/eval-lab");

    // Check that Eval Lab heading renders
    await expect(page.getByRole("heading", { name: "Eval Lab", exact: true })).toBeVisible();

    // Check that holdout seed distribution header renders
    await expect(
      page.getByText("Holdout seed distribution — reported claim surface", { exact: true }),
    ).toBeVisible();

    // Verify all 20 holdout seeds are detected
    await expect(page.getByText("20 of 20 holdout seeds present", { exact: false })).toBeVisible();

    // Verify the gate value container strictly highlights the worst holdout seed (seed 101 @ 71.00%)
    const gateLabel = page.getByText("Gate value — worst holdout seed", { exact: true });
    await expect(gateLabel).toBeVisible();

    const gateCard = page.locator("header").filter({ hasText: "Gate value — worst holdout seed" });
    await expect(gateCard).toBeVisible();
    await expect(gateCard).toContainText("71.00%");
    await expect(gateCard).toContainText("seed 101");
    await expect(gateCard).toContainText("71 / 100");

    // Verify five-number summary min (gate) line
    const minStat = page.getByText("min (gate)", { exact: true });
    await expect(minStat).toBeVisible();
    await expect(page.getByText("seed 101", { exact: false }).first()).toBeVisible();
  });
});
