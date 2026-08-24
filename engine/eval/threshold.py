"""Threshold sweeper and PR curve evaluator on dev seeds (§4.4, D15, check 3.8).

Finds the optimal guardrail confidence threshold using grid search on dev seeds only.
Saves sweep results to reports/threshold_sweep.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from engine.core.generator.build import generate_dataset
from engine.core.guardrail import GuardrailConfig, GuardrailValidator, MatchProposal
from engine.core.matching.blocker import build_candidate_space
from engine.core.matching.rules import DeterministicMatcher


def _parse_seeds(seeds_str: str) -> list[int]:
    """Parse seed string like '1-10' or '1,2,3' into list of ints."""
    if "-" in seeds_str:
        start_s, end_s = seeds_str.split("-", 1)
        return list(range(int(start_s.strip()), int(end_s.strip()) + 1))
    if "," in seeds_str:
        return [int(s.strip()) for s in seeds_str.split(",") if s.strip()]
    return [int(seeds_str.strip())]


@click.command()
@click.option("--seeds", default="1-10", help="Dev seed range to sweep (e.g. 1-10)")
@click.option(
    "--output",
    default="reports/threshold_sweep.json",
    type=click.Path(path_type=Path),
    help="Output JSON file path",
)
def main(seeds: str, output: Path) -> None:
    """Run threshold sweep across dev seeds."""
    seed_list = _parse_seeds(seeds)
    thresholds = [0.50, 0.60, 0.70, 0.80, 0.90]

    sweep_results = []
    best_f1 = -1.0
    optimal_threshold = 0.70

    for thresh in thresholds:
        tp_total = 0
        fp_total = 0
        fn_total = 0

        config = GuardrailConfig(min_confidence=thresh, min_fields=2)

        for seed in seed_list:
            dataset = generate_dataset(n=60, seed=seed)
            matcher = DeterministicMatcher()
            res = matcher.match(
                dataset.bank_txns,
                dataset.gateway_payouts,
                dataset.ledger_entries,
            )

            candidate_space = build_candidate_space(
                dataset.bank_txns,
                dataset.gateway_payouts,
                dataset.ledger_entries,
            )

            validator = GuardrailValidator(
                config=config,
                bank_txns=dataset.bank_txns,
                gateway_payouts=dataset.gateway_payouts,
                ledger_entries=dataset.ledger_entries,
            )

            # Evaluate proposals on residual bank records
            for b in dataset.bank_txns:
                # If matched by deterministic rules, skip
                if any(b.bank_id in mg.bank_ids for mg in res.matched_groups):
                    continue

                # Find candidates in candidate space
                candidates = [
                    bp[1] for bp in candidate_space.bank_payout_pairs if bp[0] == b.bank_id
                ]
                for p_id in candidates:
                    payout = dataset.payout_by_id.get(p_id)
                    if not payout:
                        continue

                    ledgers = [e for e in dataset.ledger_entries if e.reference == payout.payout_id]
                    # Simulate confidence based on delta
                    delta = abs(b.amount_paise - payout.net_paise)
                    sim_conf = max(0.40, 1.0 - (delta / 200.0))

                    proposal = MatchProposal(
                        bank_id=b.bank_id,
                        payout_id=payout.payout_id,
                        ledger_ids=[e.ledger_id for e in ledgers],
                        confidence=sim_conf,
                        fields_matched=["amount_net", "date"],
                        reason="Candidate proposal",
                    )

                    verdict = validator.validate(proposal)
                    is_true_link = any(
                        t.is_match and t.left_id == b.bank_id and t.right_id == payout.payout_id
                        for t in dataset.truth_links
                    )

                    if verdict.status == "accepted":
                        if is_true_link:
                            tp_total += 1
                        else:
                            fp_total += 1
                    else:
                        if is_true_link:
                            fn_total += 1

        prec = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else 1.0
        rec = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        if f1 > best_f1:
            best_f1 = f1
            optimal_threshold = thresh

        sweep_results.append(
            {
                "threshold": thresh,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "tp": tp_total,
                "fp": fp_total,
                "fn": fn_total,
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "seed_set": "dev",
        "seeds": seed_list,
        "optimal_threshold": optimal_threshold,
        "best_f1": round(best_f1, 4),
        "grid": sweep_results,
    }

    with output.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    click.echo(
        f"Sweep complete across {len(seed_list)} dev seeds. "
        f"Optimal threshold: {optimal_threshold} (F1: {best_f1:.4f})"
    )


if __name__ == "__main__":
    main()
