"""CLI entry point for the reconciliation engine."""

from __future__ import annotations

import click


@click.group()
def main() -> None:
    """Track 04 — AI Finance Controller CLI."""


@main.command()
@click.option("--n", default=100, help="Number of records to generate")
@click.option("--seed", default=42, help="Random seed")
def generate(n: int, seed: int) -> None:
    """Generate synthetic reconciliation data."""
    click.echo(f"Generate: n={n}, seed={seed} (not yet implemented)")


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
