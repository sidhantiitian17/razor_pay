import { test, expect } from "@playwright/test";

import seed5Fixture from "./fixtures/run_dev_seed5.json" with { type: "json" };

const MOCK_CALLS = [
  {
    call_id: "call_001",
    run_id: seed5Fixture.run_id,
    seq: 1,
    turns: 2,
    tools_used: ["fetch_candidates", "propose_match"],
    tokens_in: 1200,
    tokens_out: 350,
    cost_usd: 0.00885,
    latency_ms: 450,
    guardrail_verdict: "accepted",
    guardrail_reasons: [],
    prompt_redacted:
      "System: Reconcile payout pout_01 against bank txns [BNK-01] with amount 97640 paise.",
    response: "Propose match BNK-01 to pout_01 based on exact amount and date alignment.",
    created_at: new Date().toISOString(),
  },
  {
    call_id: "call_002",
    run_id: seed5Fixture.run_id,
    seq: 2,
    turns: 3,
    tools_used: ["fetch_candidates", "inspect_record", "propose_match"],
    tokens_in: 1850,
    tokens_out: 420,
    cost_usd: 0.0125,
    latency_ms: 620,
    guardrail_verdict: "rejected",
    guardrail_reasons: ["delta_too_large"],
    prompt_redacted: "System: Inspect candidate payout pout_02 against bank txns [BNK-02].",
    response: "Propose match BNK-02 with amount difference exceeding tolerance.",
    created_at: new Date().toISOString(),
  },
];

test.describe("Check 10.1: Agent Trace Turn Counts", () => {
  test("per-call turn counts render on Agent Trace and match agent_turns stats", async ({
    page,
  }) => {
    // Intercept runs query
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

    // Intercept agent_calls query
    await page.route("**/rest/v1/agent_calls*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_CALLS),
      });
    });

    await page.goto("/agent-trace");
    await expect(page.getByRole("heading", { name: "Agent Trace" })).toBeVisible();

    // 1. Verify timeline header columns
    await expect(page.getByText("seq", { exact: true })).toBeVisible();
    await expect(page.getByText("turns", { exact: true })).toBeVisible();
    await expect(page.getByText("tools used", { exact: true })).toBeVisible();

    // 2. Verify per-call turn counts render
    // Call 1 turns = 2
    await expect(
      page
        .locator("button", { hasText: "fetch_candidates, propose_match" })
        .getByText("2", { exact: true }),
    ).toBeVisible();
    // Call 2 turns = 3
    await expect(
      page
        .locator("button", { hasText: "fetch_candidates, inspect_record, propose_match" })
        .getByText("3", { exact: true }),
    ).toBeVisible();

    // 3. Verify reconciliation strip displays Calls traced
    await expect(page.getByText("Calls traced", { exact: true })).toBeVisible();
  });
});
