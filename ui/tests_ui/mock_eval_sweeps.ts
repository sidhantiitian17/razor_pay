import type { Page } from "@playwright/test";

function makeReport(seed: number, seedSet: "dev" | "holdout" | "regression", matchRate: number) {
  return {
    run_id: "00000000-0000-0000-0000-000000000001",
    engine_version: "0.1.0",
    schema_version: "1.0.0",
    config: {
      seed,
      seed_set: seedSet,
      n: 100,
      mode: "rules_only",
      model: "claude-haiku-4-5-20251001",
      temperature: 0.0,
      prompt_hash: "sha256:a4f07ca8152525aeb3758f13f2e929712624c03a6f6763485069e961af666e0b",
      max_turns: 6,
      concurrency: 4,
      tolerances: {
        drift_paise: 50,
        skew_days: 2,
        pct_delta: 0.01,
      },
      guardrail: {
        min_confidence: 0.7,
        min_fields: 2,
      },
    },
    candidate_space: {
      size: 1216,
      blocker_recall: {
        value: 1.0,
        numerator: 495,
        denominator: 495,
      },
    },
    throughput: {
      measurement_mode: "live",
      runs_measured: 1,
      wall_clock_seconds_median: 0.1013,
      rows_total: 595,
      rows_per_second_end_to_end: {
        value: 5871.9,
        numerator: 595,
        denominator: 101,
      },
      residuals_per_second_agent_path: {
        value: 523.0,
        numerator: 53,
        denominator: 101,
      },
      stage_seconds: {
        generate: 0.0012,
        block: 0.0625,
        match: 0.0124,
        agent: 0.0012,
        guardrail: 0.0001,
        classify: 0.0032,
        close: 0.0122,
        grade: 0.0082,
        report: 0.0001,
      },
      llm_calls: 0,
      llm_retries: 0,
      llm_p50_ms: 0.0,
      llm_p95_ms: 0.0,
      agent_turns: {
        mean: 0.0,
        max: 0,
        single_turn_fraction: 0.0,
      },
    },
    cost: {
      tokens_in: 0,
      tokens_out: 0,
      cache_hit_rate: 0.0,
      cost_usd: 0.0,
      cost_per_100_rows_usd: 0.0,
      pricing_last_verified: "2026-08-24",
    },
    accuracy: {
      match_rate: {
        value: matchRate,
        numerator: Math.round(matchRate * 100),
        denominator: 100,
      },
      resolved_rate: {
        value: 0.7412,
        numerator: 441,
        denominator: 595,
      },
      unresolved_rate: {
        value: 0.2588,
        numerator: 154,
        denominator: 595,
      },
      links: {
        bank_payout: {
          tp: 66,
          fp: 0,
          fn: 21,
          tn: 399,
          precision: {
            value: 1.0,
            numerator: 66,
            denominator: 66,
          },
          recall: {
            value: 0.7586206896551724,
            numerator: 66,
            denominator: 87,
          },
          f1: 0.8627450980392156,
        },
        payout_ledger: {
          tp: 304,
          fp: 0,
          fn: 104,
          tn: 322,
          precision: {
            value: 1.0,
            numerator: 304,
            denominator: 304,
          },
          recall: {
            value: 0.7450980392156863,
            numerator: 304,
            denominator: 408,
          },
          f1: 0.8539325842696629,
        },
      },
    },
    ablation: {
      rules_only: {
        match_rate: 0.7,
        precision: 0.98,
        cost_usd: 0.0,
      },
      agent_only: {
        match_rate: 0.65,
        precision: 0.92,
        cost_usd: 0.045,
      },
      rules_agent: {
        match_rate: 0.78,
        precision: 0.96,
        cost_usd: 0.025,
      },
      random: {
        match_rate: 0.01,
        precision: 0.08,
        cost_usd: 0.0,
      },
      agent_lift: {
        value: 0.08,
        numerator: 8,
        denominator: 100,
      },
      precision_cost: -0.02,
    },
    resolved: {
      clean: 264,
      drift: 48,
      timing_tolerated: 48,
      utr_recovered: 36,
      refund: 45,
    },
    unresolved: {
      amount_mismatch: 8,
      fee_mismatch: 8,
      timing_break: 10,
      missing_utr: 6,
      duplicate: 15,
      refund_unpaired: 8,
      orphan_bank: 3,
      orphan_ledger: 96,
      partial_group: 0,
    },
    closures: {
      applied: 0,
      dry_run: true,
      reversible: true,
      second_pass_new_closures: 0,
      closure_rate: {
        value: 0.0,
        numerator: 0,
        denominator: 441,
      },
    },
    guardrail: {
      proposals: 0,
      accepted: 0,
      rejected: 0,
      reject_reasons: {},
    },
    controls: {
      shuffled_truth: {
        passed: true,
        observed_match_rate: 0.02,
      },
      null_agent: {
        passed: true,
        identical_to_rules_only: true,
      },
      random_matcher: {
        passed: true,
        observed_precision: 0.08,
      },
      poisoned_prompt: {
        passed: true,
        leak_detector_fired: true,
      },
      inverted_rule: {
        passed: true,
        tests_failed: 7,
      },
      disabled_dedup: {
        passed: true,
        duplicate_bucket_size: 0,
      },
    },
  };
}

/**
 * Sets up Playwright route intercepts for /eval-lab tests, providing a complete
 * 20-seed holdout sweep (101-120), 10 dev seeds (1-10), and regression seed (42).
 */
export async function setupEvalLabMocks(page: Page) {
  const runId = "00000000-0000-0000-0000-000000000001";
  const runRow = {
    run_id: runId,
    engine_version: "0.1.0",
    status: "complete",
    created_at: new Date().toISOString(),
    config: { seed: 42, seed_set: "regression", n: 100, mode: "rules_only" },
    report: makeReport(42, "regression", 0.75),
  };

  const sweepRows = [];
  // 20 holdout seeds (101-120): seed 101 has the minimum match rate of 0.7100 (71.00%)
  for (let s = 101; s <= 120; s++) {
    const mr = s === 101 ? 0.71 : 0.72 + ((s * 7) % 15) * 0.01;
    sweepRows.push({
      id: s,
      run_id: runId,
      sweep_type: "holdout_sweep",
      seed: s,
      seed_set: "holdout",
      created_at: new Date().toISOString(),
      report: makeReport(s, "holdout", mr),
    });
  }

  // 10 dev seeds (1-10)
  for (let s = 1; s <= 10; s++) {
    sweepRows.push({
      id: 200 + s,
      run_id: runId,
      sweep_type: "dev_sweep",
      seed: s,
      seed_set: "dev",
      created_at: new Date().toISOString(),
      report: makeReport(s, "dev", 0.74),
    });
  }

  // 1 regression seed (42)
  sweepRows.push({
    id: 300,
    run_id: runId,
    sweep_type: "golden_snapshot",
    seed: 42,
    seed_set: "regression",
    created_at: new Date().toISOString(),
    report: makeReport(42, "regression", 0.75),
  });

  await page.route("**/rest/v1/runs*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([runRow]),
    });
  });

  await page.route("**/rest/v1/eval_sweeps*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sweepRows),
    });
  });

  await page.route("**/rest/v1/control_results*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
}
