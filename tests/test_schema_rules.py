"""Tests for report schema rules (checks 0.10-0.13).

These tests validate structural rules on the frozen report schema:
- 0.10: Every metric requires numerator + denominator (R5)
- 0.11: measurement_mode and seed_set are enums (R7, R10)
- 0.12: No top-level accuracy scalar (§4.2)
- 0.13: All six control keys required (§4.6)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "contracts" / "report.schema.json"


@pytest.fixture()
def schema() -> dict[str, object]:
    """Load the report schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture()
def validator(schema: dict[str, object]) -> Draft202012Validator:
    """Create a validator from the schema."""
    return Draft202012Validator(schema)


def _make_metric(value: float = 0.92, num: int = 92, den: int = 100) -> dict[str, object]:
    return {"value": value, "numerator": num, "denominator": den}


def _make_minimal_report(**overrides: object) -> dict[str, object]:
    """Create a minimal valid report for testing."""
    report: dict[str, object] = {
        "run_id": "00000000-0000-0000-0000-000000000001",
        "engine_version": "0.1.0",
        "schema_version": "1.0.0",
        "config": {
            "seed": 42,
            "seed_set": "holdout",
            "n": 100,
            "mode": "rules_agent",
            "model": "claude-haiku-4-5-20251001",
            "agent_backend": "heuristic",
            "temperature": 0,
            "prompt_hash": "sha256:abc123",
            "max_turns": 6,
            "concurrency": 4,
            "tolerances": {"drift_paise": 49, "skew_days": 2, "pct_delta": 0.01},
            "guardrail": {"min_confidence": 0.70, "min_fields": 2},
        },
        "candidate_space": {"size": 1180, "blocker_recall": _make_metric(1.0, 194, 194)},
        "throughput": {
            "measurement_mode": "live",
            "runs_measured": 3,
            "wall_clock_seconds_median": 12.4,
            "rows_total": 400,
            "rows_per_second_end_to_end": _make_metric(32.2, 400, 12.4),
            "residuals_per_second_agent_path": _make_metric(4.1, 41, 10.0),
            "stage_seconds": {
                "generate": 0.3,
                "block": 0.2,
                "match": 0.4,
                "agent": 10.0,
                "guardrail": 0.1,
                "classify": 0.2,
                "close": 0.7,
                "grade": 0.3,
                "report": 0.2,
            },
            "llm_calls": 12,
            "llm_retries": 0,
            "llm_p50_ms": 610,
            "llm_p95_ms": 1180,
            "agent_turns": {"mean": 2.4, "max": 5, "single_turn_fraction": 0.18},
        },
        "cost": {
            "tokens_in": 6210,
            "tokens_out": 1120,
            "cache_hit_rate": 0.71,
            "cost_usd": 0.0041,
            "cost_per_100_rows_usd": 0.0010,
            "pricing_last_verified": "2026-08-24",
        },
        "accuracy": {
            "match_rate": _make_metric(0.92, 92, 100),
            "resolved_rate": _make_metric(0.88, 352, 400),
            "unresolved_rate": _make_metric(0.12, 48, 400),
            "links": {
                "bank_payout": {
                    "tp": 88,
                    "fp": 1,
                    "fn": 5,
                    "tn": 1086,
                    "precision": _make_metric(0.989, 88, 89),
                    "recall": _make_metric(0.946, 88, 93),
                    "f1": 0.967,
                },
                "payout_ledger": {
                    "tp": 90,
                    "fp": 0,
                    "fn": 4,
                    "tn": 1086,
                    "precision": _make_metric(1.0, 90, 90),
                    "recall": _make_metric(0.957, 90, 94),
                    "f1": 0.978,
                },
            },
        },
        "ablation": {
            "rules_only": {"match_rate": 0.61, "precision": 1.0, "cost_usd": 0.0},
            "agent_only": {"match_rate": 0.74, "precision": 0.94, "cost_usd": 0.0061},
            "rules_agent": {"match_rate": 0.92, "precision": 0.989, "cost_usd": 0.0041},
            "random": {"match_rate": 0.01, "precision": 0.08, "cost_usd": 0.0},
            "agent_lift": _make_metric(0.31, 31, 100),
            "precision_cost": -0.011,
        },
        "resolved": {
            "clean": 44,
            "drift": 8,
            "timing_tolerated": 8,
            "utr_recovered": 6,
            "refund": 5,
        },
        "unresolved": {
            "amount_mismatch": 4,
            "fee_mismatch": 4,
            "timing_break": 5,
            "missing_utr": 3,
            "duplicate": 5,
            "refund_unpaired": 2,
            "orphan_bank": 3,
            "orphan_ledger": 3,
            "partial_group": 0,
        },
        "exceptions": [],
        "closures": {
            "applied": 352,
            "dry_run": False,
            "reversible": True,
            "second_pass_new_closures": 0,
            "closure_rate": _make_metric(1.0, 352, 352),
        },
        "guardrail": {
            "proposals": 47,
            "accepted": 34,
            "rejected": 13,
            "reject_reasons": {"low_confidence": 7},
        },
        "controls": {
            "shuffled_truth": {"passed": True, "observed_match_rate": 0.02},
            "null_agent": {"passed": True, "identical_to_rules_only": True},
            "random_matcher": {
                "passed": True,
                "observed_precision": 0.08,
                "observed_match_rate": 0.01,
            },
            "poisoned_prompt": {"passed": True, "leak_detector_fired": True},
            "inverted_rule": {"passed": True, "tests_failed": 7},
            "disabled_dedup": {"passed": True, "duplicate_bucket_size": 0},
        },
    }
    report.update(overrides)
    return report


class TestMetricShape:
    """0.10: A metric lacking numerator or denominator FAILS validation (R5)."""

    def test_valid_metric_passes(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        errors = list(validator.iter_errors(report))
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_metric_missing_numerator_fails(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        # Remove numerator from match_rate
        report["accuracy"]["match_rate"] = {"value": 0.92, "denominator": 100}  # type: ignore[index]
        errors = list(validator.iter_errors(report))
        assert len(errors) > 0, "Should fail when metric lacks numerator"

    def test_metric_missing_denominator_fails(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        report["accuracy"]["match_rate"] = {"value": 0.92, "numerator": 92}  # type: ignore[index]
        errors = list(validator.iter_errors(report))
        assert len(errors) > 0, "Should fail when metric lacks denominator"

    def test_bare_float_fails(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        report["accuracy"]["match_rate"] = 0.92  # type: ignore[index]
        errors = list(validator.iter_errors(report))
        assert len(errors) > 0, "Should fail when metric is a bare float"


class TestModeEnum:
    """0.11: measurement_mode and seed_set are enums (R7, R10)."""

    def test_valid_mode_passes(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        errors = list(validator.iter_errors(report))
        assert len(errors) == 0

    def test_invalid_measurement_mode(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        report["throughput"]["measurement_mode"] = "cached"  # type: ignore[index]
        errors = list(validator.iter_errors(report))
        assert len(errors) > 0, "Invalid measurement_mode should fail"

    def test_invalid_seed_set(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        report["config"]["seed_set"] = "custom"  # type: ignore[index]
        errors = list(validator.iter_errors(report))
        assert len(errors) > 0, "Invalid seed_set should fail"


class TestNoAccuracyField:
    """0.12: Schema rejects a top-level `accuracy` scalar (§4.2).

    The accuracy section exists as an object with detailed metrics,
    but a bare top-level accuracy number would be a vanity metric.
    The schema enforces that accuracy is an object, not a number.
    """

    def test_accuracy_as_number_fails(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        report["accuracy"] = 0.92  # type: ignore[assignment]
        errors = list(validator.iter_errors(report))
        assert len(errors) > 0, "Top-level accuracy as scalar should fail"


class TestControlsRequired:
    """0.13: All six control keys required (§4.6)."""

    CONTROL_KEYS: ClassVar[list[str]] = [
        "shuffled_truth",
        "null_agent",
        "random_matcher",
        "poisoned_prompt",
        "inverted_rule",
        "disabled_dedup",
    ]

    def test_all_present_passes(self, validator: Draft202012Validator) -> None:
        report = _make_minimal_report()
        errors = list(validator.iter_errors(report))
        assert len(errors) == 0

    @pytest.mark.parametrize("key", CONTROL_KEYS)
    def test_missing_control_fails(self, validator: Draft202012Validator, key: str) -> None:
        report = _make_minimal_report()
        del report["controls"][key]  # type: ignore[union-attr]
        errors = list(validator.iter_errors(report))
        assert len(errors) > 0, f"Missing control '{key}' should fail"
