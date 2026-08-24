"""CLI entry point for the reconciliation engine."""

from __future__ import annotations

from pathlib import Path

import click

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


@main.command()
@click.option("--mode", default="rules_agent", help="Matching mode")
@click.option("--seeds", default="42", help="Seed or seed range")
def run(mode: str, seeds: str) -> None:
    """Run the reconciliation pipeline."""
    click.echo(f"Run: mode={mode}, seeds={seeds} (not yet implemented)")


@main.command()
@click.argument("run_a")
@click.argument("run_b")
def compare(run_a: str, run_b: str) -> None:
    """Compare two runs and emit a metric delta table."""
    click.echo(f"Compare: {run_a} vs {run_b} (not yet implemented)")


if __name__ == "__main__":
    main()
