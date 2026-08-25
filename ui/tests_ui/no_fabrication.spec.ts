import { test, expect, type Page } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

// Matches ui/.env -- publishable/anon key, read-only under RLS, same
// credential the deployed UI itself uses.
const SUPABASE_URL = "https://dtgwbqcjblbcgclogvtv.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_LXQj3IBK6t9AZgn6TQJOmQ_eNqEvfat";

// en-IN grouping, matching src/lib/format.ts's `formatCount`.
const integer = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const count = (n: number): string => integer.format(n);

function unresolvedTotal(unresolved: Record<string, number>): number {
  return Object.values(unresolved).reduce((sum, v) => sum + v, 0);
}

/**
 * Fetches the same "latest run" row the dashboard itself reads (see
 * src/lib/use-run-report.ts) directly from Supabase's REST API, using the
 * anon key -- this is the ground truth the test compares the DOM against,
 * not a static copy that could drift from whatever is actually latest.
 */
async function fetchLatestRun(): Promise<typeof seed5Fixture> {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/runs?select=report&order=created_at.desc&limit=1`,
    { headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}` } },
  );
  if (!res.ok) throw new Error(`Supabase REST fetch failed: ${res.status} ${await res.text()}`);
  const rows = (await res.json()) as Array<{ report: typeof seed5Fixture }>;
  if (rows.length === 0) throw new Error("No runs published -- seed one before running this spec");
  return rows[0]!.report;
}

/**
 * Checks 8.1 (no_fabrication) and 8.6 (swap fixture, rerun 8.1): every KPI
 * card on the Run Dashboard equals the latest published run's own
 * report.json -- never a hardcoded or remembered value.
 */
async function assertDashboardMatchesFixture(page: Page, fixture: typeof seed5Fixture) {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Run Dashboard" })).toBeVisible();

  // Seed badge (header actions).
  await expect(page.getByText(count(fixture.config.seed), { exact: true })).toBeVisible();
  await expect(page.getByText(fixture.config.seed_set, { exact: true })).toBeVisible();
  await expect(page.getByText(fixture.engine_version, { exact: true })).toBeVisible();

  // Unresolved -- headline metric, sum of the unresolved buckets (never
  // combined with resolved tags).
  const unresolvedCount = unresolvedTotal(fixture.unresolved);
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: count(unresolvedCount) })
      .first(),
  ).toBeVisible();
  await expect(
    page.getByText(
      `${count(fixture.accuracy.unresolved_rate.numerator)} / ${count(fixture.accuracy.unresolved_rate.denominator)} in-scope items`,
      { exact: false },
    ),
  ).toBeVisible();

  // Match rate -- numerator/denominator always shown alongside the
  // percentage. Scoped to the headline `<output>` status role: the same
  // percentage can also legitimately appear in the ablation table below.
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: `${(fixture.accuracy.match_rate.value * 100).toFixed(2)}%` }),
  ).toBeVisible();
  await expect(
    page.getByText(
      `${count(fixture.accuracy.match_rate.numerator)} / ${count(fixture.accuracy.match_rate.denominator)}`,
      { exact: false },
    ),
  ).toBeVisible();

  // Resolved rate.
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: `${(fixture.accuracy.resolved_rate.value * 100).toFixed(2)}%` }),
  ).toBeVisible();

  // Confusion matrices: candidate_space_size displayed (R8). Appears 3x
  // (once per matrix caption, once as the headline stat) -- .last() is the
  // headline block per dashboard.tsx's render order.
  await expect(
    page.getByText(`${count(fixture.candidate_space.size)} pairs`, { exact: true }).last(),
  ).toBeVisible();
}

test.describe("No fabrication", () => {
  test("8.1: dashboard KPIs equal the latest published run's report.json", async ({ page }) => {
    const latest = await fetchLatestRun();
    await assertDashboardMatchesFixture(page, latest);
  });

  test("8.6: swap fixture -- the currently-latest run differs from an earlier known run, and the dashboard follows it, not the old one", async ({
    page,
  }) => {
    const latest = await fetchLatestRun();
    // seed5Fixture is a real, earlier-published run captured statically.
    // Prove the dashboard tracks whichever run is ACTUALLY latest right now
    // (not seed5, not a remembered value) by requiring they differ and
    // asserting the DOM matches the live one.
    expect(latest.run_id).not.toBe(seed5Fixture.run_id);
    expect(latest.accuracy.resolved_rate.value).not.toBe(seed5Fixture.accuracy.resolved_rate.value);
    await assertDashboardMatchesFixture(page, latest);
  });
});
