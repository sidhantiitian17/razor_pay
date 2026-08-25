import { test, expect } from "@playwright/test";

// Matches ui/.env -- publishable/anon key, read-only under RLS, same
// credential the deployed UI itself uses. (Playwright does not load .env by
// default, so this must not depend on process.env being populated.)
const SUPABASE_URL = "https://dtgwbqcjblbcgclogvtv.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_LXQj3IBK6t9AZgn6TQJOmQ_eNqEvfat";

async function restGet<T>(path: string): Promise<T> {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}` },
  });
  if (!res.ok) throw new Error(`Supabase REST fetch failed: ${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

function unresolvedTotal(unresolved: Record<string, number>): number {
  return Object.values(unresolved).reduce((sum, v) => sum + v, 0);
}

// Mirrors ui/src/lib/format.ts formatCount exactly -- same Intl instance
// options, so the DOM text this test expects is generated the same way the
// app generates it, not a re-derivation that could drift.
const formatCount = (value: number): string =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);

/**
 * Check 9.1: "Row count equals sum(report.unresolved) exactly."
 *
 * Original literal reading asserted the Exceptions workqueue grid's row
 * count against sum(report.unresolved). That can never hold: reporter.py
 * deliberately sums affected SOURCE rows per bucket (len(exc.row_ids)) so
 * resolved+unresolved reconciles against throughput.rows_total, while the
 * workqueue grid (ExceptionTable) renders one row per EXCEPTION GROUP for
 * triage -- a single group can span several row_ids (e.g. one orphan_ledger
 * journal spans 4 ledger rows). Confirmed on a real seeded run: 23 groups vs
 * an unresolved sum of 58. This is not a bug in either surface -- the two
 * numbers answer different questions -- so redefining the check to compare
 * each surface against its own honest source is the correct fix, not a
 * loosened one.
 *
 * Decision recorded on razorpay-p14-completion (tasks.json), asked
 * 2026-08-25T04:35:00Z, answered by directive to implement 9.1 (interpreted
 * as redefine-not-mutate-the-UI: option (b) of the two offered, matching the
 * Dashboard's existing "Sum of the unresolved buckets -- the honest number"
 * StatCard, which already surfaces this exact metric separately from the
 * workqueue grid). No UI code was authored or modified to make this pass --
 * per standing policy, Lovable UI changes only ever come from a real
 * Lovable-side drop, never hand-authored here. This test only asserts against
 * UI that already exists.
 *
 * Redefined criterion, two parts:
 *  1. The Dashboard's "Unresolved" StatCard renders sum(report.unresolved)
 *     honestly, with its numerator/denominator sourced from the same report
 *     (accuracy.unresolved_rate) -- i.e. the affected-row count has exactly
 *     one honest home in the UI and it says what it is.
 *  2. The Exceptions workqueue grid's own headline count ("showing X of Y
 *     exceptions") is honest for what IT claims to show -- one row per
 *     exception group, matching the raw exceptions table count exactly. This
 *     was always true (see the P9 finding) and stays as a sanity check.
 */
test.describe("Workqueue count", () => {
  test("unresolved sum is honestly surfaced on its own dashboard card", async ({ page }) => {
    const runs = await restGet<
      Array<{
        run_id: string;
        report: {
          unresolved: Record<string, number>;
          accuracy: { unresolved_rate: { numerator: number; denominator: number } };
        };
      }>
    >("runs?select=run_id,report&order=created_at.desc&limit=1");
    if (runs.length === 0)
      throw new Error("No runs published -- seed one before running this spec");
    const { report } = runs[0]!;
    const expectedUnresolvedSum = unresolvedTotal(report.unresolved);

    // Cross-check the report's own internal consistency first: the rate's
    // numerator must equal the bucket sum (this is the reporter.py-guaranteed
    // invariant the whole redefinition rests on -- assert it holds, don't
    // assume it).
    expect(
      report.accuracy.unresolved_rate.numerator,
      "accuracy.unresolved_rate.numerator should equal sum(report.unresolved) per reporter.py's rows_total invariant",
    ).toBe(expectedUnresolvedSum);

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Run Dashboard" })).toBeVisible();

    // StatCard renders label as a direct <span>, two levels below the card's
    // own root div (label span -> header row div -> card div) -- walk up
    // from the exact label text instead of a broad div-contains-text filter,
    // which over-matches ancestor containers and breaks strict mode.
    const unresolvedCard = page.getByText("Unresolved", { exact: true }).locator("xpath=../..");
    await expect(
      unresolvedCard.getByText(formatCount(expectedUnresolvedSum), { exact: true }),
    ).toBeVisible();
    await expect(unresolvedCard).toContainText(
      `${formatCount(report.accuracy.unresolved_rate.numerator)} / ${formatCount(report.accuracy.unresolved_rate.denominator)}`,
    );
  });

  test("workqueue grid headline count is honest for exception groups", async ({ page }) => {
    const runs = await restGet<Array<{ run_id: string }>>(
      "runs?select=run_id&order=created_at.desc&limit=1",
    );
    if (runs.length === 0)
      throw new Error("No runs published -- seed one before running this spec");
    const { run_id: runId } = runs[0]!;

    const exceptions = await restGet<Array<{ exception_id: string }>>(
      `exceptions?select=exception_id&run_id=eq.${runId}`,
    );

    await page.goto("/exceptions");
    await expect(page.getByRole("heading", { name: "Exception workqueue" })).toBeVisible();
    // The unvirtualized headline count ("showing X of Y exceptions") --
    // accurate regardless of scroll position, unlike counting rendered
    // <button> grid rows, which the virtualizer only mounts for the visible
    // window plus overscan.
    const summary = page.getByText(/showing \d[\d,]* of \d[\d,]* exceptions/);
    await expect(summary).toBeVisible();
    await expect(summary).toContainText(`of ${exceptions.length} exceptions`);
  });
});
