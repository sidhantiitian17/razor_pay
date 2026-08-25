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

/**
 * Check 9.1: "Row count equals sum(report.unresolved) exactly."
 *
 * engine/app/reporter.py computes `unresolved[bucket]` as the count of
 * affected SOURCE rows (len(exc.row_ids) summed per bucket) -- specifically
 * so resolved+unresolved reconciles against throughput.rows_total (see the
 * "Guarantees sum(resolved) + sum(unresolved) == rows_total" comment there).
 * A single exception can group multiple row_ids (e.g. one orphan_ledger
 * journal spans 4 ledger rows), so sum(unresolved) counts affected rows, not
 * exception groups.
 *
 * The workqueue grid (ExceptionTable) currently renders one row per
 * EXCEPTION GROUP, not one row per affected source row -- so this check is
 * expected to fail against the current UI until the grid is changed to
 * expand groups by their row_ids (or the grid gains a per-row-id view).
 * This is written to the literal IMPLEMENTATION_PLAN.md 9.1 criterion on
 * purpose, not loosened to make it pass -- see the P9 PR description for the
 * finding this documents.
 */
test.describe("Workqueue count", () => {
  test("row count equals sum of unresolved", async ({ page }) => {
    const runs = await restGet<
      Array<{ run_id: string; report: { unresolved: Record<string, number> } }>
    >("runs?select=run_id,report&order=created_at.desc&limit=1");
    if (runs.length === 0)
      throw new Error("No runs published -- seed one before running this spec");
    const { run_id: runId, report } = runs[0]!;
    const expectedUnresolvedSum = unresolvedTotal(report.unresolved);

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

    // Sanity: the summary's own "of Y" matches the raw exceptions row count
    // fetched above (both read the same unfiltered set).
    await expect(summary).toContainText(`of ${exceptions.length} exceptions`);

    // The literal 9.1 assertion: exception GROUP count vs affected-ROW sum.
    expect(
      exceptions.length,
      `exceptions table has ${exceptions.length} rows (one per exception group) but ` +
        `sum(report.unresolved) is ${expectedUnresolvedSum} (affected source rows) -- ` +
        `the workqueue grid renders one row per group, not per affected row_id, so it ` +
        `cannot equal sum(unresolved) unless the grid is changed to expand by row_ids`,
    ).toBe(expectedUnresolvedSum);
  });
});
