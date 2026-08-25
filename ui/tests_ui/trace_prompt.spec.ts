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
    prompt_redacted: {
      system:
        "Reconcile candidate payout pout_01 against bank txns [BNK-01] amount_paise: 97640 date: 2026-08-01.",
      task: "propose_match",
    },
    response: {
      status: "accepted",
      reason: "Propose match BNK-01 to pout_01 based on exact amount and date alignment.",
    },
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
    prompt_redacted: {
      system: "Inspect candidate payout pout_02 amount_paise: 50000 against bank txns [BNK-02].",
      task: "inspect_record",
    },
    response: {
      status: "rejected",
      reason: "Propose match BNK-02 with amount difference.",
    },
    created_at: new Date().toISOString(),
  },
];

const FORBIDDEN_TRUTH_TERMS = ["ground_truth", "_truth_label", "expected_group", "truth_tag"];

test.describe("Check 10.3: Zero Truth Leak in Rendered Trace Prompts", () => {
  test("no rendered prompt in the trace viewer contains a truth label", async ({ page }) => {
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

    // Click on call 1 row to open CallSheet drawer
    const firstCallButton = page.locator("button", { hasText: "fetch_candidates, propose_match" });
    await expect(firstCallButton).toBeVisible();
    await firstCallButton.click();

    // Verify CallSheet opened with prompt_redacted panel
    await expect(page.getByText("prompt_redacted", { exact: true })).toBeVisible();
    const promptText = await page.locator("pre").first().innerText();

    // Assert no forbidden truth leakage terms exist in rendered prompt
    for (const term of FORBIDDEN_TRUTH_TERMS) {
      expect(
        promptText.toLowerCase(),
        `Prompt contains forbidden truth leak '${term}'`,
      ).not.toContain(term);
    }
  });
});
