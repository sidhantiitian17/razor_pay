"""Seed sweep evaluation harness across dev and holdout seed sets.

Satisfies §4.4, §4.9, R10, checks 5.5, 5.6, 5.8.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any, Literal

from engine.app.reporter import ReportGenerator
from engine.core.generator.build import generate_dataset


def _parse_seeds(seed_str: str) -> list[int]:
    """Parse seed ranges like '101-120' or comma-separated '1,2,3'."""
    if "-" in seed_str:
        start_s, end_s = seed_str.split("-", 1)
        return list(range(int(start_s), int(end_s) + 1))
    if "," in seed_str:
        return [int(s.strip()) for s in seed_str.split(",") if s.strip()]
    return [int(seed_str)]


def _bootstrap_ci(values: list[float], n_resamples: int = 2000, alpha: float = 0.05) -> list[float]:
    """Compute seeded 95% bootstrap confidence interval."""
    if not values:
        return [0.0, 0.0]
    rng = random.Random(42)
    k = len(values)
    means: list[float] = []
    for _ in range(n_resamples):
        resample = [rng.choice(values) for _ in range(k)]
        means.append(sum(resample) / k)
    means.sort()
    low_idx = int((alpha / 2) * n_resamples)
    high_idx = int((1 - alpha / 2) * n_resamples)
    return [round(means[low_idx], 4), round(means[high_idx], 4)]


def _compute_stats(values: list[float]) -> dict[str, Any]:
    """Compute mean, stdev, min, max, and 95% bootstrap CI."""
    if not values:
        return {"mean": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0, "ci_95": [0.0, 0.0]}
    k = len(values)
    mean_val = sum(values) / k
    variance = sum((x - mean_val) ** 2 for x in values) / (k - 1) if k > 1 else 0.0
    stdev_val = math.sqrt(variance)
    min_val = min(values)
    max_val = max(values)
    ci = _bootstrap_ci(values)
    return {
        "mean": round(mean_val, 4),
        "stdev": round(stdev_val, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "ci_95": ci,
    }


def run_sweep(
    seeds: list[int],
    n: int = 100,
    mode: str = "rules_only",
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run reconciliation evaluation across a set of seeds and aggregate stats."""
    seed_set = "holdout" if any(101 <= s <= 120 for s in seeds) else "dev"
    typed_seed_set: Literal["dev", "holdout", "regression"] = (
        "holdout" if seed_set == "holdout" else "dev"
    )
    generator = ReportGenerator()

    runs: list[dict[str, Any]] = []
    match_rates: list[float] = []
    resolved_rates: list[float] = []
    unresolved_rates: list[float] = []
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for seed in seeds:
        dataset = generate_dataset(n=n, seed=seed)
        report = generator.generate_report(
            dataset=dataset,
            measurement_mode="live",
            mode="rules_only" if mode == "rules_only" else "rules_agent",
            seed=seed,
            seed_set=typed_seed_set,
            dry_run=True,
            _include_ablation=False,
        )

        acc = report["accuracy"]
        assert isinstance(acc, dict)
        mr = float(acc["match_rate"]["value"])
        rr = float(acc["resolved_rate"]["value"])
        ur = float(acc["unresolved_rate"]["value"])

        links = acc["links"]
        assert isinstance(links, dict)
        bp_links = links["bank_payout"]
        assert isinstance(bp_links, dict)

        p = float(bp_links["precision"]["value"])
        r = float(bp_links["recall"]["value"])
        f1 = float(bp_links["f1"])

        match_rates.append(mr)
        resolved_rates.append(rr)
        unresolved_rates.append(ur)
        precisions.append(p)
        recalls.append(r)
        f1s.append(f1)

        runs.append(
            {
                "seed": seed,
                "match_rate": mr,
                "resolved_rate": rr,
                "unresolved_rate": ur,
                "precision": p,
                "recall": r,
                "f1": f1,
            }
        )

    summary = {
        "match_rate": _compute_stats(match_rates),
        "resolved_rate": _compute_stats(resolved_rates),
        "unresolved_rate": _compute_stats(unresolved_rates),
        "precision": _compute_stats(precisions),
        "recall": _compute_stats(recalls),
        "f1": _compute_stats(f1s),
    }

    result: dict[str, Any] = {
        "seeds": seeds,
        "n": n,
        "seed_set": seed_set,
        "runs": runs,
        "summary": summary,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    return result


def main() -> None:
    """CLI entrypoint for running seed sweeps."""
    parser = argparse.ArgumentParser(description="Run seed sweep evaluation.")
    parser.add_argument("--seeds", default="101-120", help="Seed range or list (e.g. 101-120)")
    parser.add_argument("--n", type=int, default=100, help="Number of cases per seed (>=50)")
    parser.add_argument("--mode", default="rules_only", help="Arm mode: rules_only, rules_agent")
    parser.add_argument(
        "--output", default="reports/sweep.json", help="Output path for sweep report"
    )
    parser.add_argument("--publish", action="store_true", help="Publish sweep rows to storage")
    parser.add_argument(
        "--db", default="data/reconciliation.db", help="Target DB path or 'supabase'"
    )
    parser.add_argument("--run-id", default=None, help="Associated run ID to link sweeps")

    args = parser.parse_args()
    seeds = _parse_seeds(args.seeds)
    output_p = Path(args.output)

    run_sweep(seeds=seeds, n=args.n, mode=args.mode, output_path=output_p)
    print(f"Saved seed sweep report to {output_p}")

    if args.publish:
        from typing import cast

        from engine.cli import _resolve_storage_adapter

        store = _resolve_storage_adapter(db=args.db)
        generator = ReportGenerator()
        run_id = args.run_id or "00000000-0000-0000-0000-000000000000"
        sweep_rows: list[dict[str, Any]] = []
        typed_mode = cast("Literal['rules_only', 'agent_only', 'rules_agent', 'random']", args.mode)
        for s in seeds:
            s_set = "holdout" if 101 <= s <= 120 else "dev" if 1 <= s <= 10 else "regression"
            typed_set = cast("Literal['dev', 'holdout', 'regression']", s_set)
            dset = generate_dataset(n=args.n, seed=s)
            s_rep = generator.generate_report(
                dataset=dset,
                mode=typed_mode,
                seed=s,
                seed_set=typed_set,
                dry_run=True,
            )
            sweep_rows.append(
                {
                    "sweep_type": "holdout_sweep" if s_set == "holdout" else "dev_sweep",
                    "seed": s,
                    "seed_set": s_set,
                    "report": s_rep,
                }
            )
        store.save_eval_sweeps(run_id=run_id, sweeps=sweep_rows)
        print(f"Published {len(sweep_rows)} sweep rows to {args.db} for run {run_id}")


if __name__ == "__main__":
    main()
