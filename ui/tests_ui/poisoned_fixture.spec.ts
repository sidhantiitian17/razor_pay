import { test, expect } from "@playwright/test";

import goldenFixture from "./fixtures/run_p10_golden.json" with { type: "json" };
import poisonedFixture from "./fixtures/run_p10_poisoned.json" with { type: "json" };
import { computeAntiSlopChecks, type VerifyInputs } from "../src/lib/anti-slop-checks";

// Matches ui/.env -- publishable/anon key, read-only under RLS, same
// credential the deployed UI itself uses.
const SUPABASE_URL = "https://dtgwbqcjblbcgclogvtv.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_LXQj3IBK6t9AZgn6TQJOmQ_eNqEvfat";

const POISONED_RUN_ID = poisonedFixture.run_id;

async function fetchLatestRunId(): Promise<string> {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/runs?select=run_id&order=created_at.desc&limit=1`,
    { headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}` } },
  );
  if (!res.ok) throw new Error(`Supabase REST fetch failed: ${res.status} ${await res.text()}`);
  const rows = (await res.json()) as Array<{ run_id: string }>;
  if (rows.length === 0) throw new Error("No runs published");
  return rows[0]!.run_id;
}

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

  // Live DOM proof against the actual deployed page. Guarded with a loud,
  // visible assertion (not a silent skip/fallback) if another agent's
  // publish raced ahead of the fixture seeded for this test -- the fix in
  // that case is to reseed the poisoned run as latest, not to let the test
  // pass vacuously.
  test("Verify page: renders fail for Rates reconcile on the live poisoned run", async ({
    page,
  }) => {
    const latestRunId = await fetchLatestRunId();
    expect(
      latestRunId,
      "another run was published after the P10 poisoned fixture was seeded as latest -- reseed it before running this test",
    ).toBe(POISONED_RUN_ID);

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
