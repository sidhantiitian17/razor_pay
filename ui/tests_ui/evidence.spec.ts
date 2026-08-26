import { test, expect } from "@playwright/test";

import { operatorRestGet, signInTestOperator } from "./auth-helpers";

// RLS now requires a signed-in operator (anon has no SELECT grant) -- see
// auth-helpers.ts. Token cached per test file, not per call.
let cachedToken: string | undefined;
async function restGet<T>(path: string): Promise<T> {
  cachedToken ??= (await signInTestOperator()).access_token;
  return operatorRestGet<T>(path, cachedToken);
}

interface ExceptionRow {
  exception_id: string;
  evidence: string[];
}

/**
 * Check 9.4: "Every exception shows >= 2 evidence strings matching the
 * report." Two literal parts, both checked without heuristics:
 *  1. Data: every exception row in the `exceptions` table has
 *     evidence.length >= 2 (this is what R6/R9 actually require -- not a
 *     line-count heuristic on the sheet's rendered text).
 *  2. UI: the ExceptionSheet's "Evidence" panel renders an <ol> with one
 *     <li> per evidence string (see components/exceptions/exception-sheet.tsx)
 *     -- opened for a real exception and matched against the exact strings
 *     fetched from the API, not just "at least N lines of something".
 */
test.describe("Evidence count", () => {
  test("every exception shows at least 2 evidence strings", async ({ page }) => {
    const runs = await restGet<Array<{ run_id: string }>>(
      "runs?select=run_id&order=created_at.desc&limit=1",
    );
    if (runs.length === 0)
      throw new Error("No runs published -- seed one before running this spec");
    const runId = runs[0]!.run_id;

    const exceptions = await restGet<ExceptionRow[]>(
      `exceptions?select=exception_id,evidence&run_id=eq.${runId}`,
    );
    expect(exceptions.length, "no exceptions on the latest run").toBeGreaterThan(0);

    const thin = exceptions.filter((e) => e.evidence.length < 2);
    expect(
      thin.map((e) => `${e.exception_id} (${e.evidence.length})`),
      "exceptions with fewer than 2 evidence strings",
    ).toEqual([]);

    // UI-level: open the sheet for the first exception and verify every one
    // of its evidence strings is literally rendered, no more and no fewer.
    const target = exceptions[0]!;

    await page.goto("/exceptions");
    await expect(page.getByRole("heading", { name: "Exception workqueue" })).toBeVisible();

    const row = page.getByRole("button").filter({ hasText: target.exception_id });
    await row.click();

    const sheet = page.getByRole("dialog");
    await expect(sheet).toBeVisible();

    const evidencePanel = sheet.locator(".panel", { hasText: "Evidence" });
    const items = evidencePanel.locator("ol li");
    await expect(items).toHaveCount(target.evidence.length);
    for (const line of target.evidence) {
      await expect(evidencePanel.getByText(line, { exact: true })).toBeVisible();
    }
  });
});
