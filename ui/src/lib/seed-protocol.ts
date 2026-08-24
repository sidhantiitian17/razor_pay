import type { SeedSet } from "@/types/report";

/**
 * The seed protocol is fixed by the engine contract, not chosen here:
 *   dev        = seeds 1-10    (tuning only, never a reported claim)
 *   holdout    = seeds 101-120 (every reported number; the 20-point sweep)
 *   regression = seed 42       (golden snapshot only, not a metric claim)
 */
export interface SeedSetSpec {
  set: SeedSet;
  label: string;
  /** Human-readable declared range, rendered verbatim in validation copy. */
  range: string;
  /** How the set may be used, shown next to every figure from it. */
  claimNote: string;
  seeds: readonly number[];
  contains: (seed: number) => boolean;
}

function span(from: number, to: number): number[] {
  return Array.from({ length: to - from + 1 }, (_, i) => from + i);
}

export const DEV_SEEDS = span(1, 10);
export const HOLDOUT_SEEDS = span(101, 120);
export const REGRESSION_SEEDS = [42];

export const SEED_SETS: Record<SeedSet, SeedSetSpec> = {
  dev: {
    set: "dev",
    label: "dev",
    range: "1–10",
    claimNote: "tuning — not a claim",
    seeds: DEV_SEEDS,
    contains: (seed) => Number.isInteger(seed) && seed >= 1 && seed <= 10,
  },
  holdout: {
    set: "holdout",
    label: "holdout",
    range: "101–120",
    claimNote: "reported claim surface",
    seeds: HOLDOUT_SEEDS,
    contains: (seed) => Number.isInteger(seed) && seed >= 101 && seed <= 120,
  },
  regression: {
    set: "regression",
    label: "regression",
    range: "42",
    claimNote: "snapshot only — not a metric claim",
    seeds: REGRESSION_SEEDS,
    contains: (seed) => seed === 42,
  },
};

export const SEED_SET_ORDER: readonly SeedSet[] = ["holdout", "dev", "regression"];

/** The set a seed belongs to, or null when it is outside every declared range. */
export function resolveSeedSet(seed: number): SeedSet | null {
  for (const spec of Object.values(SEED_SETS)) {
    if (spec.contains(seed)) return spec.set;
  }
  return null;
}

/** True when the row's declared seed_set actually contains its seed. */
export function seedMatchesDeclaredSet(seed: number, declared: string): boolean {
  const spec = (SEED_SETS as Record<string, SeedSetSpec | undefined>)[declared];
  return spec ? spec.contains(seed) : false;
}

export const SEED_RANGE_SUMMARY = `dev ${SEED_SETS.dev.range} · regression ${SEED_SETS.regression.range} · holdout ${SEED_SETS.holdout.range}`;
