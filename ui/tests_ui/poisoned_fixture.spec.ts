import { test, expect } from "@playwright/test";

import goldenFixture from "./fixtures/run_p10_golden.json" with { type: "json" };
import poisonedFixture from "./fixtures/run_p10_poisoned.json" with { type: "json" };
import { computeAntiSlopChecks, type VerifyInputs } from "../src/lib/anti-slop-checks";

const POISONED_RUN_ID = poisonedFixture.run_id;

function emptyInputs(report: typeof goldenFixture): VerifyInputs {
  // computeAntiSlopChecks is fed report + calls/closures/exceptions rows.
  // Empty arrays make checks 4/6/7 vacuous rather than pass/fail -- they are
  // not what this check is poisoning, so vacuous is the correct, honest
  // verdict for them here, not a workaround.
  return {
    report: report as unknown as VerifyInputs["report"],
    calls: [],
    closures: [],
    exceptions: [],
  };
}

test.describe("Check 10.6: golden vs poisoned fixture", () => {
  // Deterministic, race-free proof that computeAntiSlopChecks -- the exact
  // function the Verify page renders -- passes cleanly on a genuine,
  // unmodified published report and fails specifically (not globally) on one
  // with a single tampered field. This does not depend on which run is
  // "latest" in the shared database, so it cannot flake from a concurrent
  // publish by another agent or CI job.
  test("computeAntiSlopChecks: rates_reconcile passes on the golden report", () => {
    const checks = computeAntiSlopChecks(emptyInputs(goldenFixture));
    const rates = checks.find((c) => c.id === "rates_reconcile");
    expect(rates?.verdict).toBe("pass");
    // No check should fail on a genuine, untampered report.
    const failed = checks.filter((c) => c.verdict === "fail");
    expect(failed, `unexpected failures on golden fixture: ${JSON.stringify(failed)}`).toEqual([]);
  });

  test("computeAntiSlopChecks: rates_reconcile fails on the poisoned report, other checks unaffected", () => {
    const checks = computeAntiSlopChecks(emptyInputs(poisonedFixture));
    const rates = checks.find((c) => c.id === "rates_reconcile");
    expect(rates?.verdict).toBe("fail");
    // resolved_rate.value was the only field tampered (0.9025 -> 0.95);
    // unresolved_rate.value (0.0975), numerator/denominator, and every other
    // metric are untouched, so every other check must still pass or be
    // vacuous -- proving the fail is selective, not a global break.
    const listReconciles = checks.find((c) => c.id === "list_reconciles");
    const provenance = checks.find((c) => c.id === "metric_provenance");
    const costHonesty = checks.find((c) => c.id === "cost_honesty");
    expect(listReconciles?.verdict).toBe("pass");
    expect(provenance?.verdict).toBe("pass");
    expect(costHonesty?.verdict).toBe("pass");
  });

  // Live DOM proof against the actual deployed page. Intercepts the runs query
  // to deterministically supply the poisoned fixture, ensuring the test is immune
  // to concurrent publishes or shared-database staleness.
  test("Verify page: renders fail for Rates reconcile on the live poisoned run", async ({
    page,
  }) => {
    await page.route("**/rest/v1/runs*", async (route) => {
      const runRow = {
        run_id: POISONED_RUN_ID,
        engine_version: "0.1.0",
        status: "complete",
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        report: poisonedFixture,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([runRow]),
      });
    });

    await page.goto("/verify");
    await expect(page.getByRole("heading", { name: "Verify" })).toBeVisible();

    const ratesRow = page.locator("li", { hasText: "Rates reconcile" });
    await expect(ratesRow.getByText("fail", { exact: true })).toBeVisible();
    await expect(ratesRow.getByText(/resolved_rate 0\.95/)).toBeVisible();

    // Selectivity, visible in the DOM too: an unrelated check on the same
    // run still shows pass.
    const reconcileRow = page.locator("li", { hasText: "Exception list reconciles" });
    await expect(reconcileRow.getByText("pass", { exact: true })).toBeVisible();
  });
});
