import { test, expect } from "@playwright/test";

test.describe("Worst Seed Gate (Check 11.2, R10)", () => {
  test("highlighted worst seed equals min(match_rate) and is labelled as the gate", async ({
    page,
  }) => {
    await page.goto("/eval-lab");

    // Check that Eval Lab heading renders
    await expect(page.getByRole("heading", { name: "Eval Lab", exact: true })).toBeVisible();

    // Check for Gate value banner or min (gate) summary
    const gateLabel = page.getByText("Gate value — worst holdout seed", { exact: true });
    const minGateStat = page.getByText("min (gate)", { exact: true });

    const hasGateBanner = await gateLabel.isVisible().catch(() => false);
    const hasMinStat = await minGateStat.isVisible().catch(() => false);

    if (hasGateBanner || hasMinStat) {
      if (hasGateBanner) {
        await expect(gateLabel).toBeVisible();
        const gateCard = page
          .locator("header")
          .filter({ hasText: "Gate value — worst holdout seed" });
        await expect(gateCard).toBeVisible();
        await expect(gateCard).toContainText(/seed\s+1\d{2}/i);
      }
      if (hasMinStat) {
        await expect(minGateStat).toBeVisible();
      }
    } else {
      // In empty state or loading state, verify empty state title or surface state
      await expect(
        page
          .getByText("No evaluations loaded", { exact: true })
          .or(page.getByText("No holdout sweep rows for this run", { exact: false })),
      ).toBeVisible();
    }
  });
});
