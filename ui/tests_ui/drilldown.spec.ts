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

/**
 * Mirrors ui/src/lib/use-exception-sources.ts classifySourceId: a source ID
 * is routed to its table by prefix only, never by row_ids array position
 * (the previous version of this spec assumed a fixed [bank, payout, ledger]
 * position, which does not hold -- e.g. a "duplicate" exception's row_ids
 * has a single payout id at position 0).
 */
type SourceKind = "bank" | "payout" | "ledger" | "unknown";

function classifySourceId(id: string): SourceKind {
  if (id.startsWith("BNK-")) return "bank";
  if (id.startsWith("pout_SYNTH")) return "payout";
  if (id.startsWith("LED-")) return "ledger";
  return "unknown";
}

interface ExceptionRow {
  exception_id: string;
  row_ids: string[];
}

/**
 * Check 9.3: "Every row_id in the sheet exists in the source tables -- no
 * invented records." Verified two ways against the live latest run:
 *  1. Every row_id across every exception, classified by prefix, is checked
 *     against its real table (source_bank/source_payout/source_ledger --
 *     the actual migration names, not the "bank_txns/payouts/ledger_entries"
 *     the previous version of this spec guessed).
 *  2. The actual drilldown UI (ExceptionSheet, opened by clicking a
 *     workqueue row) is opened for one exception, and the IDs it renders are
 *     cross-checked the same way -- proving the check against what a human
 *     actually sees, not just the API.
 */
test.describe("Drilldown validity", () => {
  test("every row_id in the sheet exists in the source tables", async ({ page }) => {
    const runs = await restGet<Array<{ run_id: string }>>(
      "runs?select=run_id&order=created_at.desc&limit=1",
    );
    if (runs.length === 0)
      throw new Error("No runs published -- seed one before running this spec");
    const runId = runs[0]!.run_id;

    const exceptions = await restGet<ExceptionRow[]>(
      `exceptions?select=exception_id,row_ids&run_id=eq.${runId}`,
    );
    expect(
      exceptions.length,
      "no exceptions on the latest run -- nothing to drill into",
    ).toBeGreaterThan(0);

    const bankIds = new Set<string>();
    const payoutIds = new Set<string>();
    const ledgerIds = new Set<string>();
    const unknownIds: string[] = [];
    for (const exc of exceptions) {
      for (const id of exc.row_ids) {
        const kind = classifySourceId(id);
        if (kind === "bank") bankIds.add(id);
        else if (kind === "payout") payoutIds.add(id);
        else if (kind === "ledger") ledgerIds.add(id);
        else unknownIds.push(id);
      }
    }
    expect(unknownIds, `row_ids with no recognised prefix: ${unknownIds.join(", ")}`).toEqual([]);

    // 1. API-level cross-check against the real tables.
    if (bankIds.size > 0) {
      const rows = await restGet<Array<{ bank_id: string }>>(
        `source_bank?select=bank_id&run_id=eq.${runId}&bank_id=in.(${[...bankIds].join(",")})`,
      );
      const found = new Set(rows.map((r) => r.bank_id));
      const missing = [...bankIds].filter((id) => !found.has(id));
      expect(missing, `bank row_ids not found in source_bank: ${missing.join(", ")}`).toEqual([]);
    }
    if (payoutIds.size > 0) {
      const rows = await restGet<Array<{ payout_id: string }>>(
        `source_payout?select=payout_id&run_id=eq.${runId}&payout_id=in.(${[...payoutIds].join(",")})`,
      );
      const found = new Set(rows.map((r) => r.payout_id));
      const missing = [...payoutIds].filter((id) => !found.has(id));
      expect(missing, `payout row_ids not found in source_payout: ${missing.join(", ")}`).toEqual(
        [],
      );
    }
    if (ledgerIds.size > 0) {
      const rows = await restGet<Array<{ ledger_id: string }>>(
        `source_ledger?select=ledger_id&run_id=eq.${runId}&ledger_id=in.(${[...ledgerIds].join(",")})`,
      );
      const found = new Set(rows.map((r) => r.ledger_id));
      const missing = [...ledgerIds].filter((id) => !found.has(id));
      expect(missing, `ledger row_ids not found in source_ledger: ${missing.join(", ")}`).toEqual(
        [],
      );
    }

    // 2. UI-level check: open the real drilldown sheet for one exception
    // that references a bank id (a timing_break exception: [bank_id,
    // payout_id]), and verify the IDs rendered in the sheet are the exact
    // ones just proven to exist above.
    const timingBreak = exceptions.find((e) => classifySourceId(e.row_ids[0] ?? "") === "bank");
    expect(
      timingBreak,
      "expected at least one bank-referencing exception to drill into",
    ).toBeTruthy();

    await page.goto("/exceptions");
    await expect(page.getByRole("heading", { name: "Exception workqueue" })).toBeVisible();

    const row = page.getByRole("button").filter({ hasText: timingBreak!.exception_id });
    await row.click();

    const sheet = page.getByRole("dialog");
    await expect(sheet).toBeVisible();
    await expect(sheet.getByText(timingBreak!.exception_id)).toBeVisible();

    for (const id of timingBreak!.row_ids) {
      await expect(sheet.getByText(id, { exact: true })).toBeVisible();
    }
  });
});
