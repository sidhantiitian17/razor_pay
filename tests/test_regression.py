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
        measurement_mode="replay",
        mode="rules_only",
        seed_set="dev",
        seeds=[42],
        dry_run=False,
    )

    dataset2 = generate_dataset(n=60, seed=42)
    gen2 = ReportGenerator()
    report2 = gen2.generate_report(
        dataset=dataset2,
        measurement_mode="replay",
        mode="rules_only",
        seed_set="dev",
        seeds=[42],
        dry_run=False,
    )

    # Normalize dynamic UUIDs and wall-clock timings before comparing byte identity
    for r in [report1, report2]:
        r["run_id"] = "00000000-0000-0000-0000-000000000000"
        tp = r["throughput"]
        assert isinstance(tp, dict)
        tp["wall_clock_seconds_median"] = 1.0
        stage_sec = tp["stage_seconds"]
        assert isinstance(stage_sec, dict)
        tp["stage_seconds"] = {k: 0.1 for k in stage_sec}
        tp["rows_per_second_end_to_end"] = {"value": 100.0, "numerator": 100, "denominator": 1.0}
        tp["residuals_per_second_agent_path"] = {
            "value": 10.0,
            "numerator": 10,
            "denominator": 1.0,
        }

    s1 = json.dumps(report1, sort_keys=True, indent=2)
    s2 = json.dumps(report2, sort_keys=True, indent=2)
    assert s1 == s2
