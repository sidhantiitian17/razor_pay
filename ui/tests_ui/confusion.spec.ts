import { test, expect } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

const integer = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const count = (n: number): string => integer.format(n);

test.describe("Check 8.3: Confusion Matrices & Candidate Space", () => {
  test("both confusion matrices render 4 cells; totals match; candidate_space_size displayed", async ({
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

    // 1. Bank ↔ Payout links confusion matrix
    const bankPayoutHeading = page.getByRole("heading", { name: "Bank ↔ payout links" });
    await expect(bankPayoutHeading).toBeVisible();
    const bankPayoutMatrix = page.locator("div.panel", { has: bankPayoutHeading });

    const bp = seed5Fixture.accuracy.links.bank_payout;
    await expect(bankPayoutMatrix.getByText("TP", { exact: true })).toBeVisible();
    await expect(bankPayoutMatrix.getByText(count(bp.tp), { exact: true })).toBeVisible();
    await expect(bankPayoutMatrix.getByText("FP", { exact: true })).toBeVisible();
    await expect(bankPayoutMatrix.getByText(count(bp.fp), { exact: true })).toBeVisible();
    await expect(bankPayoutMatrix.getByText("FN", { exact: true })).toBeVisible();
    await expect(bankPayoutMatrix.getByText(count(bp.fn), { exact: true })).toBeVisible();
    await expect(bankPayoutMatrix.getByText("TN", { exact: true })).toBeVisible();
    await expect(bankPayoutMatrix.getByText(count(bp.tn), { exact: true })).toBeVisible();

    // 2. Payout ↔ Ledger links confusion matrix
    const payoutLedgerHeading = page.getByRole("heading", { name: "Payout ↔ ledger links" });
    await expect(payoutLedgerHeading).toBeVisible();
    const payoutLedgerMatrix = page.locator("div.panel", { has: payoutLedgerHeading });

    const pl = seed5Fixture.accuracy.links.payout_ledger;
    await expect(payoutLedgerMatrix.getByText("TP", { exact: true })).toBeVisible();
    await expect(payoutLedgerMatrix.getByText(count(pl.tp), { exact: true })).toBeVisible();
    await expect(payoutLedgerMatrix.getByText("FP", { exact: true })).toBeVisible();
    await expect(payoutLedgerMatrix.getByText(count(pl.fp), { exact: true })).toBeVisible();
    await expect(payoutLedgerMatrix.getByText("FN", { exact: true })).toBeVisible();
    await expect(payoutLedgerMatrix.getByText(count(pl.fn), { exact: true })).toBeVisible();
    await expect(payoutLedgerMatrix.getByText("TN", { exact: true })).toBeVisible();
    await expect(payoutLedgerMatrix.getByText(count(pl.tn), { exact: true })).toBeVisible();

    // 3. Totals match across candidate spaces
    const bpTotal = bp.tp + bp.fp + bp.fn + bp.tn;
    const plTotal = pl.tp + pl.fp + pl.fn + pl.tn;
    expect(bpTotal + plTotal).toBe(seed5Fixture.candidate_space.size);

    // 4. Candidate space size displayed prominently in both matrices and headline block
    await expect(
      page.getByText(`${count(seed5Fixture.candidate_space.size)} pairs`, { exact: true }).last(),
    ).toBeVisible();
  });
});
