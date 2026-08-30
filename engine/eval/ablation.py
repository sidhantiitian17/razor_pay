"""4-arm ablation evaluation harness (§4.5, R8, D7, check 5.7).

Evaluates rules_only, agent_only, rules_agent, and random arms across holdout seeds,
measuring agent_lift and precision_cost.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from engine.app.reporter import ReportGenerator
from engine.core.generator.build import generate_dataset
from engine.eval.controls import run_negative_controls


def _parse_seeds(seed_str: str) -> list[int]:
    """Parse seed string into integer list."""
    if "-" in seed_str:
        start_s, end_s = seed_str.split("-", 1)
        return list(range(int(start_s), int(end_s) + 1))
    if "," in seed_str:
        return [int(s.strip()) for s in seed_str.split(",") if s.strip()]
    return [int(seed_str)]


def run_ablation(
    seeds: list[int],
    n: int = 100,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run 4-arm ablation across seeds and compute lift & precision cost."""
    seed_set = "holdout" if any(101 <= s <= 120 for s in seeds) else "dev"
    typed_seed_set: Literal["dev", "holdout", "regression"] = (
        "holdout" if seed_set == "holdout" else "dev"
    )
    generator = ReportGenerator()

    rules_only_mr: list[float] = []
    rules_only_p: list[float] = []
    rules_only_cost: list[float] = []

    agent_only_mr: list[float] = []
    agent_only_p: list[float] = []
    agent_only_cost: list[float] = []

    rules_agent_mr: list[float] = []
    rules_agent_p: list[float] = []
    rules_agent_cost: list[float] = []

    random_mr: list[float] = []
    random_p: list[float] = []
    random_cost: list[float] = []

    for seed in seeds:
        dataset = generate_dataset(n=n, seed=seed)

        # Arm 1: rules_only
        rep_rules = generator.generate_report(
            dataset=dataset,
            mode="rules_only",
            seed=seed,
            seed_set=typed_seed_set,
            dry_run=True,
            _include_ablation=False,
        )
        acc_r = rep_rules["accuracy"]
        assert isinstance(acc_r, dict)
        mr_r = float(acc_r["match_rate"]["value"])
        p_r = float(acc_r["links"]["bank_payout"]["precision"]["value"])
        rules_only_mr.append(mr_r)
        rules_only_p.append(p_r)
        rules_only_cost.append(0.0)

        # Arm 2: agent_only
        rep_agent = generator.generate_report(
            dataset=dataset,
            mode="agent_only",
            seed=seed,
            seed_set=typed_seed_set,
            dry_run=True,
            _include_ablation=False,
        )
        acc_a = rep_agent["accuracy"]
        assert isinstance(acc_a, dict)
        mr_a = float(acc_a["match_rate"]["value"])
        p_a = float(acc_a["links"]["bank_payout"]["precision"]["value"])
        agent_only_mr.append(mr_a)
        agent_only_p.append(p_a)
        cost_a = rep_agent["cost"]
        assert isinstance(cost_a, dict)
        agent_only_cost.append(float(cost_a["cost_usd"]))

        # Arm 3: rules_agent
        rep_ra = generator.generate_report(
            dataset=dataset,
            mode="rules_agent",
            seed=seed,
            seed_set=typed_seed_set,
            dry_run=True,
            _include_ablation=False,
        )
        acc_ra = rep_ra["accuracy"]
        assert isinstance(acc_ra, dict)
        mr_ra = float(acc_ra["match_rate"]["value"])
        p_ra = float(acc_ra["links"]["bank_payout"]["precision"]["value"])
        rules_agent_mr.append(mr_ra)
        rules_agent_p.append(p_ra)
        cost_ra = rep_ra["cost"]
        assert isinstance(cost_ra, dict)
        rules_agent_cost.append(float(cost_ra["cost_usd"]))

        # Arm 4: random — sourced from the negative-controls random matcher
        # (engine/eval/controls.py), a real random sampler graded against
        # truth, not a hardcoded chance-floor guess.
        controls_res = run_negative_controls(dataset=dataset, save_to_disk=False)
        random_mr.append(float(controls_res["random_matcher"]["observed_match_rate"]))
        random_p.append(float(controls_res["random_matcher"]["observed_precision"]))
        random_cost.append(0.0)

    avg_r_mr = sum(rules_only_mr) / len(rules_only_mr)
    avg_r_p = sum(rules_only_p) / len(rules_only_p)

    avg_a_mr = sum(agent_only_mr) / len(agent_only_mr)
    avg_a_p = sum(agent_only_p) / len(agent_only_p)

    avg_ra_mr = sum(rules_agent_mr) / len(rules_agent_mr)
    avg_ra_p = sum(rules_agent_p) / len(rules_agent_p)

    avg_rnd_mr = sum(random_mr) / len(random_mr)
    avg_rnd_p = sum(random_p) / len(random_p)

    # Report the genuine lift, even when it is zero or negative. A previous
    # version clamped a non-positive result up to a hardcoded 0.05 — a
    # fabricated positive lift that contradicts the "never estimate" contract
    # and disagreed with the per-run reporter, which never clamped.
    agent_lift = round(avg_ra_mr - avg_r_mr, 4)
    precision_cost = round(avg_ra_p - avg_r_p, 4)

    ablation_result: dict[str, Any] = {
        "seeds": seeds,
        "n": n,
        "arms": {
            "rules_only": {
                "match_rate": round(avg_r_mr, 4),
                "precision": round(avg_r_p, 4),
                "cost_usd": round(sum(rules_only_cost) / len(rules_only_cost), 4),
            },
            "agent_only": {
                "match_rate": round(avg_a_mr, 4),
                "precision": round(avg_a_p, 4),
                "cost_usd": round(sum(agent_only_cost) / len(agent_only_cost), 4),
            },
            "rules_agent": {
                "match_rate": round(avg_ra_mr, 4),
                "precision": round(avg_ra_p, 4),
                "cost_usd": round(sum(rules_agent_cost) / len(rules_agent_cost), 4),
            },
            "random": {
                "match_rate": round(avg_rnd_mr, 4),
                "precision": round(avg_rnd_p, 4),
                "cost_usd": round(sum(random_cost) / len(random_cost), 4),
            },
        },
        "agent_lift": {
            "value": agent_lift,
            "numerator": int(agent_lift * 100),
            "denominator": 100,
        },
        "precision_cost": precision_cost,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(ablation_result, f, indent=2)

    return ablation_result


def main() -> None:
    """CLI entrypoint for running ablation analysis."""
    parser = argparse.ArgumentParser(description="Run 4-arm ablation evaluation.")
    parser.add_argument("--seeds", default="101-120", help="Seed range or list (e.g. 101-120)")
    parser.add_argument("--n", type=int, default=100, help="Number of cases per seed (>=50)")
    parser.add_argument("--output", default="reports/ablation.json", help="Output report path")

    args = parser.parse_args()
    seeds = _parse_seeds(args.seeds)
    output_p = Path(args.output)

    run_ablation(seeds=seeds, n=args.n, output_path=output_p)
    print(f"Saved ablation report to {output_p}")


if __name__ == "__main__":
    main()
