"""CLI entry point for the reconciliation engine."""

from __future__ import annotations

from pathlib import Path

import click

from engine.app.reporter import generate_reconciliation_report, write_baseline_report
from engine.core.generator.build import generate_dataset


@click.group()
def main() -> None:
    """Track 04 — AI Finance Controller CLI."""


@main.command()
@click.option("--n", default=100, type=int, help="Number of records to generate")
@click.option("--seed", default=42, type=int, help="Random seed")
@click.option(
    "--out",
    default="data",
    type=click.Path(path_type=Path),
    help="Output directory for generated CSVs",
)
def generate(n: int, seed: int, out: Path) -> None:
    """Generate synthetic reconciliation data."""
    dataset = generate_dataset(n=n, seed=seed)
    dataset.write_csvs(out)
    click.echo(
        f"Generated {len(dataset.bank_txns)} bank txns, "
        f"{len(dataset.gateway_payouts)} payouts, "
        f"{len(dataset.ledger_entries)} ledger entries in {out}"
    )


def _parse_seeds(seeds_str: str) -> list[int]:
    """Parse seed string like '42' or '101-120' or '1,2,3' into list of ints."""
    if "-" in seeds_str:
        start_s, end_s = seeds_str.split("-", 1)
        return list(range(int(start_s.strip()), int(end_s.strip()) + 1))
    if "," in seeds_str:
        return [int(s.strip()) for s in seeds_str.split(",") if s.strip()]
    return [int(seeds_str.strip())]


def _classify_seed_set(seed: int) -> str:
    """Classify a seed per the frozen protocol.

    IMPLEMENTATION_PLAN.md §4.4: dev = 1-10 (tuning only), holdout = 101-120
    (the only reported claim), regression = 42 (golden snapshot only). Any
    other seed is rejected rather than silently mislabeled -- a seed outside
    all three declared ranges has no defined seed_set to report under.
    """
    if seed == 42:
        return "regression"
    if 1 <= seed <= 10:
        return "dev"
    if 101 <= seed <= 120:
        return "holdout"
    raise click.BadParameter(
        f"seed {seed} is outside all declared seed sets "
        "(dev 1-10, holdout 101-120, regression 42) -- see IMPLEMENTATION_PLAN.md §4.4"
    )


@main.command()
@click.option(
    "--mode",
    default="rules_only",
    type=click.Choice(["rules_only", "agent_only", "rules_agent", "random"]),
    help="Matching mode",
)
@click.option("--seeds", default="42", help="Seed or seed range (e.g. 101-120)")
@click.option("--n", default=100, type=int, help="Number of records per seed")
@click.option(
    "--report-out",
    default="reports/baseline.json",
    type=click.Path(path_type=Path),
    help="Output path for the report JSON",
)
def run(mode: str, seeds: str, n: int, report_out: Path) -> None:
    """Run the reconciliation pipeline."""
    seed_list = _parse_seeds(seeds)
    click.echo(f"Running mode={mode} across {len(seed_list)} seed(s)...")

    # For holdout range (101-120), generate aggregate or first holdout baseline
    first_seed = seed_list[0]
    seed_set = _classify_seed_set(first_seed)

    dataset = generate_dataset(n=n, seed=first_seed)
    report = generate_reconciliation_report(
        dataset=dataset,
        mode=mode,
        seed=first_seed,
        seed_set=seed_set,
    )

    write_baseline_report(report, report_out)
    click.echo(f"Baseline report successfully published to {report_out}")


@main.command()
@click.argument("run_a")
@click.argument("run_b")
def compare(run_a: str, run_b: str) -> None:
    """Compare two runs and emit a metric delta table."""
    click.echo(f"Compare: {run_a} vs {run_b} (not yet implemented)")


if __name__ == "__main__":
    main()
