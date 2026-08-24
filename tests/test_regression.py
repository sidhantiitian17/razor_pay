"""Tests for golden report regression and replay stability (§4.4, check 5.10)."""

import json

from engine.app.reporter import ReportGenerator
from engine.core.generator.build import generate_dataset


def test_golden_report_replay() -> None:
    """Check 5.10: Golden report byte-identical under deterministic replay (seed=42)."""
    dataset1 = generate_dataset(n=60, seed=42)
    gen1 = ReportGenerator()
    report1 = gen1.generate_report(
        dataset=dataset1,
        measurement_mode="rules_only",
        seed_set="dev",
        seeds=[42],
        dry_run=False,
    )

    dataset2 = generate_dataset(n=60, seed=42)
    gen2 = ReportGenerator()
    report2 = gen2.generate_report(
        dataset=dataset2,
        measurement_mode="rules_only",
        seed_set="dev",
        seeds=[42],
        dry_run=False,
    )

    # Strip dynamic timestamps and timing fields before comparing byte identity
    for r in [report1, report2]:
        r["timestamp"] = "2026-08-25T00:00:00Z"
        r["timings"] = {
            "wall_clock_seconds": 1.0,
            "stage_seconds": {k: 0.1 for k in r["timings"]["stage_seconds"]},
        }

    s1 = json.dumps(report1, sort_keys=True, indent=2)
    s2 = json.dumps(report2, sort_keys=True, indent=2)
    assert s1 == s2
