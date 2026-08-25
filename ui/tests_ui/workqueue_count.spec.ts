import { test, expect } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";

test.describe("Workqueue count", () => {
  let expectedUnresolvedSum: number;

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
    const unresolved = (report.unresolved as Record<string, number>) || {};
    expectedUnresolvedSum = Object.values(unresolved).reduce((sum, v) => sum + v, 0);
  });

  test("row count equals sum of unresolved", async ({ page }) => {
    await page.goto("/exceptions");
    // Wait for the table to be visible
    await page.waitForSelector("table", { state: "visible" });
    // Count rows in tbody
    const rowCount = await page.locator("tbody tr").count();
    expect(rowCount).toBe(expectedUnresolvedSum);
  });
});
