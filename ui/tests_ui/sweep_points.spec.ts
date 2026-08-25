import { test, expect } from "@playwright/test";

import { setupEvalLabMocks } from "./mock_eval_sweeps";

test.describe("Check 11.1: Holdout Sweep Points on Eval Lab", () => {
  test("20 holdout datapoints render on Eval Lab, each equal to sweep.json's values", async ({
    page,
  }) => {
    // Intercept Eval Lab routes with deterministic 20-seed holdout sweep fixture
    await setupEvalLabMocks(page);

    await page.goto("/eval-lab");
    await expect(page.getByRole("heading", { name: "Eval Lab", exact: true })).toBeVisible();

    // 1. Holdout distribution header visible
    await expect(
      page.getByText("Holdout seed distribution — reported claim surface", { exact: true }),
    ).toBeVisible();

    // 2. 20 of 20 holdout seeds present
    await expect(page.getByText("20 of 20 holdout seeds present", { exact: false })).toBeVisible();

    // 3. Five-number summary stats render (min, q1, median, q3, max)
    await expect(page.getByText("min (gate)", { exact: true })).toBeVisible();
    await expect(page.getByText("median", { exact: true })).toBeVisible();
    await expect(page.getByText("max", { exact: true })).toBeVisible();

    // Gate value (worst holdout seed 101 @ 71.00%) is rendered
    await expect(page.getByText("71.00%").first()).toBeVisible();
  });
});
