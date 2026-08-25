import { test, expect } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";

test.describe("Drilldown validity", () => {
  test.beforeAll(async () => {
    const supabaseUrl = process.env.VITE_SUPABASE_URL;
    const supabaseAnonKey = process.env.VITE_SUPABASE_ANON_KEY;
    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error(
        "Supabase environment variables VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set",
      );
    }
    const supabase = createClient(supabaseUrl, supabaseAnonKey);
    const { data, error } = await supabase
      .from("runs")
      .select("report")
      .order("created_at", { ascending: false })
      .limit(1)
      .single();
    const report = data?.report as Record<string, unknown> | null;
    if (!report) throw new Error("No report found in the latest run");
    const exceptions = (report.exceptions as Array<{ row_ids?: string[] }>) || [];
    // We'll check each exception's row_ids against the source tables.
    // Assume row_ids order: [bank_txn_id, payout_id, ledger_id]
    const bankIds = new Set();
    const payoutIds = new Set();
    const ledgerIds = new Set();
    for (const exc of exceptions) {
      const ids = (exc.row_ids as string[]) || [];
      if (ids.length >= 1) bankIds.add(ids[0]);
      if (ids.length >= 2) payoutIds.add(ids[1]);
      if (ids.length >= 3) ledgerIds.add(ids[2]);
    }
    // Check bank_txns
    for (const id of bankIds) {
      const { data: bankData, error: bankErr } = await supabase
        .from("bank_txns")
        .select("id")
        .eq("id", id)
        .single();
      if (bankErr) throw new Error(`Bank txn ${id} not found: ${bankErr.message}`);
      if (!bankData) throw new Error(`Bank txn ${id} not found`);
    }
    // Check payouts
    for (const id of payoutIds) {
      const { data: payoutData, error: payoutErr } = await supabase
        .from("payouts")
        .select("id")
        .eq("id", id)
        .single();
      if (payoutErr) throw new Error(`Payout ${id} not found: ${payoutErr.message}`);
      if (!payoutData) throw new Error(`Payout ${id} not found`);
    }
    // Check ledger_entries
    for (const id of ledgerIds) {
      const { data: ledgerData, error: ledgerErr } = await supabase
        .from("ledger_entries")
        .select("id")
        .eq("id", id)
        .single();
      if (ledgerErr) throw new Error(`Ledger entry ${id} not found: ${ledgerErr.message}`);
      if (!ledgerData) throw new Error(`Ledger entry ${id} not found`);
    }
  });

  test("every row_id in the sheet exists in source tables", async ({ page }) => {
    // If we reach here, all checks passed in beforeAll.
    // We can optionally visit the page to ensure the UI loads.
    await page.goto("/exceptions");
    await page.waitForSelector("table", { state: "visible" });
    // No further assertions needed; the beforeAll already validated.
  });
});
