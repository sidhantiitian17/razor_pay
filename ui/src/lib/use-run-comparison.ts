import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";
import type { Config, MetricValue, ReconciliationReport } from "@/types/report";

export interface RunListRow {
  run_id: string;
  engine_version: string;
  status: string;
  created_at: string;
  config: Config | null;
  report: ReconciliationReport | null;
}

const RUN_COLUMNS = "run_id, engine_version, status, created_at, config, report";

const sel = (s: string): string => s;

async function fetchRuns(): Promise<RunListRow[]> {
  const { data, error } = await supabase
    .from("runs")
    .select(sel(RUN_COLUMNS))
    .order("created_at", { ascending: false })
    .limit(50)
    .returns<RunListRow[]>();

  if (error) throw new Error(error.message);
  return data ?? [];
}

async function fetchRunCount(): Promise<number> {
  const { count, error } = await supabase
    .from("runs")
    .select("run_id", { count: "exact", head: true });

  if (error) throw new Error(error.message);
  return count ?? 0;
}

/** Runs available to the comparison selectors, newest first. */
export function useRuns() {
  return useQuery({
    queryKey: ["runs", "list"] as const,
    queryFn: fetchRuns,
    enabled: isBackendConfigured(),
    staleTime: 30_000,
  });
}

/** Exact row count for public live stats; not derived from the bounded runs list. */
export function useRunCount(enabled = true) {
  return useQuery({
    queryKey: ["runs", "count"] as const,
    queryFn: fetchRunCount,
    enabled: enabled && isBackendConfigured(),
    staleTime: 30_000,
  });
}

type Polarity = "higher" | "lower";

export interface MetricSpec {
  id: string;
  label: string;
  group: string;
  polarity: Polarity;
  /** |delta| at or below this reads as unchanged. */
  epsilon: number;
  format: (value: number) => string;
  pick: (report: ReconciliationReport) => MetricValue | number | null;
}

const pct = (value: number): string => `${(value * 100).toFixed(2)}%`;
const ms = (value: number): string => `${value.toFixed(0)} ms`;
const rate = (value: number): string => `${value.toFixed(2)} rows/s`;
const usd4 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});
const count = (value: number): string => value.toFixed(0);

function unresolvedTotal(report: ReconciliationReport): number {
  return Object.values(report.unresolved).reduce((sum, value) => sum + value, 0);
}

export const COMPARISON_METRICS: readonly MetricSpec[] = [
  {
    id: "match_rate",
    label: "match rate",
    group: "accuracy",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.match_rate,
  },
  {
    id: "resolved_rate",
    label: "resolved rate",
    group: "accuracy",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.resolved_rate,
  },
  {
    id: "unresolved_rate",
    label: "unresolved rate",
    group: "accuracy",
    polarity: "lower",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.unresolved_rate,
  },
  {
    id: "unresolved_total",
    label: "unresolved items (sum of buckets)",
    group: "accuracy",
    polarity: "lower",
    epsilon: 0,
    format: count,
    pick: (r) => unresolvedTotal(r),
  },
  {
    id: "blocker_recall",
    label: "blocker recall",
    group: "candidate space",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.candidate_space.blocker_recall,
  },
  {
    id: "candidate_space",
    label: "candidate space size",
    group: "candidate space",
    polarity: "lower",
    epsilon: 0,
    format: count,
    pick: (r) => r.candidate_space.size,
  },
  {
    id: "bank_payout_precision",
    label: "bank↔payout precision",
    group: "links",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.links.bank_payout.precision,
  },
  {
    id: "bank_payout_recall",
    label: "bank↔payout recall",
    group: "links",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.links.bank_payout.recall,
  },
  {
    id: "bank_payout_f1",
    label: "bank↔payout F1",
    group: "links",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.links.bank_payout.f1,
  },
  {
    id: "payout_ledger_precision",
    label: "payout↔ledger precision",
    group: "links",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.links.payout_ledger.precision,
  },
  {
    id: "payout_ledger_recall",
    label: "payout↔ledger recall",
    group: "links",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.links.payout_ledger.recall,
  },
  {
    id: "payout_ledger_f1",
    label: "payout↔ledger F1",
    group: "links",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.accuracy.links.payout_ledger.f1,
  },
  {
    id: "closure_rate",
    label: "closure rate",
    group: "closures",
    polarity: "higher",
    epsilon: 1e-6,
    format: pct,
    pick: (r) => r.closures.closure_rate,
  },
  {
    id: "cost_usd",
    label: "cost",
    group: "cost & throughput",
    polarity: "lower",
    epsilon: 1e-6,
    format: (v) => usd4.format(v),
    pick: (r) => r.cost.cost_usd,
  },
  {
    id: "cost_per_100",
    label: "cost per 100 rows",
    group: "cost & throughput",
    polarity: "lower",
    epsilon: 1e-6,
    format: (v) => usd4.format(v),
    pick: (r) => r.cost.cost_per_100_rows_usd,
  },
  {
    id: "rows_per_second",
    label: "rows/s end-to-end",
    group: "cost & throughput",
    polarity: "higher",
    epsilon: 1e-4,
    format: rate,
    pick: (r) => r.throughput.rows_per_second_end_to_end,
  },
  {
    id: "llm_p95",
    label: "LLM p95 latency",
    group: "cost & throughput",
    polarity: "lower",
    epsilon: 0,
    format: ms,
    pick: (r) => r.throughput.llm_p95_ms,
  },
];

export type Direction = "improved" | "regressed" | "unchanged" | "incomparable";

export interface MetricDelta {
  id: string;
  label: string;
  group: string;
  polarity: Polarity;
  a: number | null;
  b: number | null;
  aProvenance: string | null;
  bProvenance: string | null;
  delta: number | null;
  formatted: { a: string; b: string; delta: string };
  direction: Direction;
  note: string | null;
}

function isMetricValue(value: MetricValue | number): value is MetricValue {
  return typeof value === "object";
}

function provenance(value: MetricValue | number | null): string | null {
  if (value === null || !isMetricValue(value)) return null;
  return `${value.numerator} / ${value.denominator}`;
}

export interface ComparisonResult {
  rows: MetricDelta[];
  /** Set when the two runs' seed_sets differ — every row is then incomparable. */
  incomparableReason: string | null;
  improved: number;
  regressed: number;
  unchanged: number;
}

/**
 * Polarity-aware diff of two reports. A dev-set number is not comparable to a
 * holdout claim, so mismatched seed_sets refuse the comparison rather than
 * printing a delta.
 */
export function compareReports(
  a: ReconciliationReport | null,
  b: ReconciliationReport | null,
): ComparisonResult {
  const incomparableReason =
    a && b && a.config.seed_set !== b.config.seed_set
      ? `seed_set differs (${a.config.seed_set} vs ${b.config.seed_set}) — a ${a.config.seed_set}-set figure is not comparable to a ${b.config.seed_set}-set figure`
      : null;

  const rows = COMPARISON_METRICS.map<MetricDelta>((spec) => {
    const rawA = a ? spec.pick(a) : null;
    const rawB = b ? spec.pick(b) : null;
    const valueA = rawA === null ? null : isMetricValue(rawA) ? rawA.value : rawA;
    const valueB = rawB === null ? null : isMetricValue(rawB) ? rawB.value : rawB;

    const comparable = valueA !== null && valueB !== null && incomparableReason === null;
    const delta = comparable ? (valueB as number) - (valueA as number) : null;

    let direction: Direction = "incomparable";
    if (comparable && delta !== null) {
      if (Math.abs(delta) <= spec.epsilon) direction = "unchanged";
      else if (spec.polarity === "higher") direction = delta > 0 ? "improved" : "regressed";
      else direction = delta < 0 ? "improved" : "regressed";
    }

    return {
      id: spec.id,
      label: spec.label,
      group: spec.group,
      polarity: spec.polarity,
      a: valueA,
      b: valueB,
      aProvenance: provenance(rawA),
      bProvenance: provenance(rawB),
      delta,
      formatted: {
        a: valueA === null ? "—" : spec.format(valueA),
        b: valueB === null ? "—" : spec.format(valueB),
        delta:
          delta === null
            ? "not comparable"
            : `${delta > 0 ? "+" : delta < 0 ? "−" : ""}${spec.format(Math.abs(delta))}`,
      },
      direction,
      note:
        incomparableReason ??
        (valueA === null || valueB === null ? "one side has no report yet" : null),
    };
  });

  return {
    rows,
    incomparableReason,
    improved: rows.filter((row) => row.direction === "improved").length,
    regressed: rows.filter((row) => row.direction === "regressed").length,
    unchanged: rows.filter((row) => row.direction === "unchanged").length,
  };
}
