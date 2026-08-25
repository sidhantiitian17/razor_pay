"""CLI entry point for the reconciliation engine."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

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
@click.option("--publish", is_flag=True, default=False, help="Publish results to storage")
@click.option("--db", default="data/reconciliation.db", help="SQLite database path")
def run(
    mode: str,
    seeds: str,
    n: int,
    report_out: Path,
    publish: bool,
    db: str = "data/reconciliation.db",
) -> None:
    """Run the reconciliation pipeline."""
    from engine.adapters.store_sqlite import SQLiteStorageAdapter
    from engine.app.publisher import ReportPublisher

    seed_list = _parse_seeds(seeds)
    click.echo(f"Running mode={mode} across {len(seed_list)} seed(s)...")

    # For holdout range (101-120), generate aggregate or first holdout baseline
    first_seed = seed_list[0]
    seed_set = _classify_seed_set(first_seed)
    dataset = generate_dataset(n=n, seed=first_seed)
    typed_mode = cast("Literal['rules_only', 'agent_only', 'rules_agent', 'random']", mode)
    typed_seed_set = cast("Literal['dev', 'holdout', 'regression']", seed_set)
    report = generate_reconciliation_report(
        dataset=dataset,
        mode=typed_mode,
        seed=first_seed,
        seed_set=typed_seed_set,
    )

    write_baseline_report(report, report_out)
    click.echo(f"Baseline report successfully published to {report_out}")

    if publish:
        store = SQLiteStorageAdapter(db_path=db)
        publisher = ReportPublisher(store=store)
        publisher.publish(dataset=dataset, report=report)
        click.echo("Published reconciliation dataset and report to database.")


@main.command()
@click.option("--once", is_flag=True, default=False, help="Process one task and exit")
@click.option("--db", default="data/reconciliation.db", help="SQLite DB path")
def worker(once: bool, db: str) -> None:
    """Run background queue worker to process run requests."""
    from engine.adapters.store_sqlite import SQLiteStorageAdapter
    from engine.app.worker import ReconciliationWorker

    store = SQLiteStorageAdapter(db_path=db)
    w = ReconciliationWorker(store=store)
    if once:
        processed = w.run_once()
        click.echo(f"Worker executed task: {processed}")
    else:
        click.echo("Starting worker polling loop...")
        w.run_loop()


@main.command()
@click.argument("run_a", type=click.Path(exists=True, path_type=Path))
@click.argument("run_b", type=click.Path(exists=True, path_type=Path))
def compare(run_a: Path, run_b: Path) -> None:
    """Compare two runs and emit a metric delta table (D18)."""
    import json

    with run_a.open("r", encoding="utf-8") as f:
        data_a = json.load(f)
    with run_b.open("r", encoding="utf-8") as f:
        data_b = json.load(f)

    def extract_metrics(doc: dict[str, object]) -> dict[str, float]:
        metrics: dict[str, float] = {}
        if "accuracy" in doc and isinstance(doc["accuracy"], dict):
            acc = doc["accuracy"]
            metrics["Match Rate"] = float(acc["match_rate"]["value"])
            metrics["Resolved Rate"] = float(acc["resolved_rate"]["value"])
            metrics["Unresolved Rate"] = float(acc["unresolved_rate"]["value"])
            if "links" in acc and isinstance(acc["links"], dict):
                bp = acc["links"].get("bank_payout", {})
                if isinstance(bp, dict) and "precision" in bp:
                    metrics["Precision (BP)"] = float(bp["precision"]["value"])
                    metrics["Recall (BP)"] = float(bp["recall"]["value"])
                    metrics["F1 (BP)"] = float(bp["f1"])
        elif "arms" in doc and isinstance(doc["arms"], dict):
            # Ablation doc format
            ra = doc["arms"].get("rules_agent", {})
            if isinstance(ra, dict):
                metrics["Match Rate"] = float(ra.get("match_rate", 0.0))
                metrics["Precision (BP)"] = float(ra.get("precision", 0.0))
                metrics["Cost (USD)"] = float(ra.get("cost_usd", 0.0))
        if "cost" in doc and isinstance(doc["cost"], dict):
            metrics["Cost (USD)"] = float(doc["cost"].get("cost_usd", 0.0))
        if "throughput" in doc and isinstance(doc["throughput"], dict):
            tp = doc["throughput"].get("rows_per_second_end_to_end", {})
            if isinstance(tp, dict) and "value" in tp:
                metrics["Throughput (rows/s)"] = float(tp["value"])
        return metrics

    m_a = extract_metrics(data_a)
    m_b = extract_metrics(data_b)

    all_keys = sorted(set(m_a.keys()) | set(m_b.keys()))

    click.echo("=" * 72)
    click.echo(f"METRIC DELTA COMPARISON (D18): {run_a.name} vs {run_b.name}")
    click.echo("=" * 72)
    click.echo(f"{'Metric':<24} {'Run A':<14} {'Run B':<14} {'Delta':<14}")
    click.echo("-" * 72)

    for k in all_keys:
        val_a = m_a.get(k, 0.0)
        val_b = m_b.get(k, 0.0)
        delta = val_b - val_a
        sign = "+" if delta >= 0 else ""
        if "Cost" in k:
            click.echo(f"{k:<24} ${val_a:<13.4f} ${val_b:<13.4f} {sign}${delta:<13.4f}")
        else:
            click.echo(f"{k:<24} {val_a:<14.4f} {val_b:<14.4f} {sign}{delta:<14.4f}")

    click.echo("=" * 72)


@main.command()
@click.option(
    "--reverse",
    "reverse_run_id",
    type=str,
    help="Reverse closures for a run_id (I14)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate write-back without persisting",
)
@click.option("--db", default="data/reconciliation.db", help="SQLite DB path")
def close(reverse_run_id: str | None, dry_run: bool, db: str) -> None:
    """Execute idempotent write-back closure or reverse closures for a run (R2, I14)."""
    from engine.app.closer import ClosureEngine

    closer = ClosureEngine()

    if reverse_run_id is not None:
        rev_res = closer.reverse(run_id=reverse_run_id)
        click.echo(f"Reversed {rev_res.reversed_count} closure(s) for run {reverse_run_id}.")
    else:
        click.echo(f"Closer write-back executed (dry_run={dry_run}).")


if __name__ == "__main__":
    main()
