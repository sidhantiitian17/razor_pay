"""Tests for report schema, denominators, totals, and timings (checks 5.1, 5.3, 5.4, 5.12, 5.13)."""

import json
from pathlib import Path

import jsonschema
from engine.app.reporter import ReportGenerator
from engine.core.generator.build import generate_dataset


def _make_sample_report() -> dict[str, object]:
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    return generator.generate_report(
        dataset=dataset,
        measurement_mode="live",
        mode="rules_only",
        seed_set="holdout",
        seeds=[42],
        dry_run=False,
    )


def test_schema() -> None:
    """Check 5.1: report.json validates against the frozen schema (draft 2020-12)."""
    schema_path = Path("contracts/report.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    report = _make_sample_report()
    jsonschema.validate(instance=report, schema=schema)


def test_denominators() -> None:
    """Check 5.3: I11 — every metric object has numerator and denominator (R5)."""
    report = _make_sample_report()

    def check_metrics(node: object) -> None:
        if isinstance(node, dict):
            if "value" in node and ("numerator" in node or "denominator" in node):
                assert "numerator" in node, f"Missing numerator in metric {node}"
                assert "denominator" in node, f"Missing denominator in metric {node}"
                assert isinstance(node["numerator"], (int, float))
                assert isinstance(node["denominator"], (int, float))
            for v in node.values():
                check_metrics(v)
        elif isinstance(node, list):
            for item in node:
                check_metrics(item)

    check_metrics(report)


def test_totals_reconcile() -> None:
    """Check 5.4: sum(resolved) + sum(unresolved) == rows_total (R6, D5)."""
    report = _make_sample_report()
    throughput = report["throughput"]
    resolved = report["resolved"]
    unresolved = report["unresolved"]

    assert isinstance(throughput, dict)
    assert isinstance(resolved, dict)
    assert isinstance(unresolved, dict)

    rows_total = throughput["rows_total"]
    resolved_sum = sum(v for v in resolved.values() if isinstance(v, int))
    unresolved_sum = sum(v for v in unresolved.values() if isinstance(v, int))

    assert resolved_sum + unresolved_sum == rows_total


def test_exception_evidence() -> None:
    """Check 5.12: Every exception in report carries evidence >= 2 and proposed action (R6, R9)."""
    report = _make_sample_report()
    exceptions = report["exceptions"]
    assert isinstance(exceptions, list)
    assert len(exceptions) > 0

    for ex in exceptions:
        assert isinstance(ex, dict)
        assert "evidence" in ex
        assert isinstance(ex["evidence"], list)
        assert len(ex["evidence"]) >= 2
        assert "proposed_action" in ex
        assert ex["proposed_action"] != ""


def test_stage_seconds() -> None:
    """Check 5.13: All 9 stage timings present and summing within 5% of wall clock (R7)."""
    report = _make_sample_report()
    throughput = report["throughput"]
    assert isinstance(throughput, dict)

    stage_seconds = throughput["stage_seconds"]
    assert isinstance(stage_seconds, dict)

    expected_stages = {
        "generate",
        "block",
        "match",
        "agent",
        "guardrail",
        "classify",
        "close",
        "grade",
        "report",
    }
    assert expected_stages.issubset(stage_seconds.keys())

    total_stage_time = sum(v for v in stage_seconds.values() if isinstance(v, (int, float)))
    wall_clock = throughput["wall_clock_seconds_median"]
    assert isinstance(wall_clock, (int, float))

    # Assert within 5% of wall clock (or minimal duration)
    assert wall_clock > 0
    assert abs(total_stage_time - wall_clock) <= max(0.05 * wall_clock, 0.05)


def test_fast_flag_emits_null_ablation_not_fabricated_arms() -> None:
    """`--fast` skips the companion ablation reruns and emits ablation: null.

    The value must be an honest null, never a block of zeroed/placeholder
    arms, and the report must still validate against the frozen schema.
    """
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(
        dataset=dataset,
        mode="rules_agent",
        seed=42,
        seed_set="holdout",
        seeds=[42],
        fast=True,
    )

    assert report["ablation"] is None

    schema = json.loads(Path("contracts/report.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=report, schema=schema)

    # A non-fast run of the same dataset still produces a full 4-arm block.
    full = generator.generate_report(
        dataset=dataset,
        mode="rules_agent",
        seed=42,
        seed_set="holdout",
        seeds=[42],
    )
    ablation = full["ablation"]
    assert isinstance(ablation, dict)
    assert {"rules_only", "agent_only", "rules_agent", "random"}.issubset(ablation)
