import { test, expect } from "@playwright/test";

test.describe("Seed Set Separation & Labels (Check 11.3, §4.4)", () => {
  test("dev seeds are visually separated and labelled 'tuning — not a claim'", async ({ page }) => {
    await page.goto("/eval-lab");

    // Check that Eval Lab header renders
    await expect(page.getByRole("heading", { name: "Eval Lab", exact: true })).toBeVisible();

    // Check seed protocol notice in header actions
    await expect(
      page.getByText("dev 1–10 · regression 42 · holdout 101–120", { exact: true }),
    ).toBeVisible();

    // Check Dev seeds panel and label
    const devHeader = page.getByRole("heading", { name: "Dev seeds 1–10", exact: true });
    const hasDevHeader = await devHeader.isVisible().catch(() => false);

    if (hasDevHeader) {
      await expect(devHeader).toBeVisible();

      // Verify the explicit note "tuning — not a claim" is present
      await expect(page.getByText("tuning — not a claim", { exact: true })).toBeVisible();

      // Verify Regression seed panel and label
      await expect(
        page.getByRole("heading", { name: "Regression seed 42", exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText("snapshot only — not a metric claim", { exact: true }),
      ).toBeVisible();

      // Verify Holdout distribution claim note
      await expect(
        page.getByText("Holdout seed distribution — reported claim surface", { exact: true }),
      ).toBeVisible();
    } else {
      // In empty state, verify description explicitly states dev seeds are tuning and not a claim
      await expect(
        page.getByText(
          "Reported numbers come from the holdout sweep only; the worst holdout seed is the gate value. Dev seeds are tuning and are never a claim, and the regression seed is a snapshot, not a metric.",
          { exact: true },
        ),
      ).toBeVisible();
    }
  });
});
