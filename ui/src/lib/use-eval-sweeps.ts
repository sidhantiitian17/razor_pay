import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";
import { SEED_SETS, seedMatchesDeclaredSet } from "@/lib/seed-protocol";
import type { MetricValue, ReconciliationReport, SeedSet } from "@/types/report";

export interface EvalSweepRow {
  id: number;
  run_id: string;
  sweep_type: string;
  seed: number;
  seed_set: string;
  report: ReconciliationReport | null;
  created_at: string;
}

const SWEEP_COLUMNS = "id, run_id, sweep_type, seed, seed_set, report, created_at";

const sel = (s: string): string => s;

async function fetchEvalSweeps(runId: string): Promise<EvalSweepRow[]> {
  const { data, error } = await supabase
    .from("eval_sweeps")
    .select(sel(SWEEP_COLUMNS))
    .eq("run_id", runId)
    .order("seed", { ascending: true })
    .returns<EvalSweepRow[]>();

  if (error) throw new Error(error.message);
  return data ?? [];
}

export function useEvalSweeps(runId: string | undefined) {
  return useQuery({
    queryKey: ["eval-sweeps", runId ?? "none"] as const,
    queryFn: () => fetchEvalSweeps(runId as string),
    enabled: isBackendConfigured() && Boolean(runId),
    staleTime: 15_000,
  });
}

/** One seed's match rate, keeping its provenance attached. */
export interface SeedPoint {
  id: number;
  seed: number;
  seedSet: string;
  /** False when the row's seed falls outside its declared set's range. */
  inDeclaredRange: boolean;
  matchRate: MetricValue;
  report: ReconciliationReport;
  createdAt: string;
}

export interface BoxStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  count: number;
}

function quantile(sorted: readonly number[], p: number): number {
  const last = sorted.length - 1;
  const pos = p * last;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  const loValue = sorted[lo] as number;
  if (lo === hi) return loValue;
  const hiValue = sorted[hi] as number;
  return loValue + (hiValue - loValue) * (pos - lo);
}

export function boxStats(values: readonly number[]): BoxStats | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return {
    min: sorted[0] as number,
    q1: quantile(sorted, 0.25),
    median: quantile(sorted, 0.5),
    q3: quantile(sorted, 0.75),
    max: sorted[sorted.length - 1] as number,
    count: sorted.length,
  };
}

export interface SweepSplit {
  points: Record<SeedSet, SeedPoint[]>;
  /** Rows whose seed_set is not one of the three declared sets. */
  undeclared: SeedPoint[];
  /** Rows present but carrying no report yet. */
  withoutReport: EvalSweepRow[];
  holdoutStats: BoxStats | null;
  /** Minimum holdout match rate — the gate value. Ties resolve to lowest seed. */
  worstHoldout: SeedPoint | null;
}

function toPoint(row: EvalSweepRow, report: ReconciliationReport): SeedPoint {
  return {
    id: row.id,
    seed: row.seed,
    seedSet: row.seed_set,
    inDeclaredRange: seedMatchesDeclaredSet(row.seed, row.seed_set),
    matchRate: report.accuracy.match_rate,
    report,
    createdAt: row.created_at,
  };
}

/**
 * Splits a sweep by seed_set. Holdout is the only set that feeds the box plot
 * and the gate value; dev and regression are kept strictly separate.
 */
export function splitSweep(rows: readonly EvalSweepRow[]): SweepSplit {
  const points: Record<SeedSet, SeedPoint[]> = { dev: [], holdout: [], regression: [] };
  const undeclared: SeedPoint[] = [];
  const withoutReport: EvalSweepRow[] = [];

  for (const row of rows) {
    if (!row.report) {
      withoutReport.push(row);
      continue;
    }
    const point = toPoint(row, row.report);
    if (row.seed_set in SEED_SETS) {
      points[row.seed_set as SeedSet].push(point);
    } else {
      undeclared.push(point);
    }
  }

  const holdout = points.holdout;
  const holdoutStats = boxStats(holdout.map((point) => point.matchRate.value));

  let worstHoldout: SeedPoint | null = null;
  for (const point of holdout) {
    if (
      worstHoldout === null ||
      point.matchRate.value < worstHoldout.matchRate.value ||
      (point.matchRate.value === worstHoldout.matchRate.value && point.seed < worstHoldout.seed)
    ) {
      worstHoldout = point;
    }
  }

  return { points, undeclared, withoutReport, holdoutStats, worstHoldout };
}
