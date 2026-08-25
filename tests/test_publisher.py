"""Tests for report publishing and persistence (§5.2, §7 P6, checks 6.1, 6.2, 6.3, 6.7, 6.8)."""

from __future__ import annotations

import json

from engine.adapters.store_memory import MemoryStorageAdapter
from engine.adapters.store_sqlite import SQLiteStorageAdapter
from engine.app.publisher import ReportPublisher
from engine.app.reporter import ReportGenerator
from engine.core.generator.build import generate_dataset


def test_round_trip() -> None:
    """Check 6.1: Publish then read back yields an identical report.json."""
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_agent", seed=42)

    store = MemoryStorageAdapter()
    publisher = ReportPublisher(store=store)

    run_id = str(report["run_id"])
    publisher.publish(dataset=dataset, report=report)

    loaded_report = publisher.load_report(run_id=run_id)
    assert loaded_report is not None
    assert loaded_report == report


def test_no_secrets() -> None:
    """Check 6.2: No published row contains an API key, auth header, or truth label."""
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_agent", seed=42)

    store = MemoryStorageAdapter()
    publisher = ReportPublisher(store=store)
    publisher.publish(dataset=dataset, report=report)

    # Check all stored tables in adapter
    dump_str = json.dumps(store.dump_all(), default=str)
    assert "sk-ant-" not in dump_str
    assert "Bearer " not in dump_str
    assert "x-api-key" not in dump_str
    assert "authorization" not in dump_str.lower()
    assert "cohort=" not in dump_str


def test_idempotent() -> None:
    """Check 6.3: Re-publishing the same run_id updates, never duplicates."""
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_agent", seed=42)

    store = MemoryStorageAdapter()
    publisher = ReportPublisher(store=store)

    # First publish
    publisher.publish(dataset=dataset, report=report)
    first_dump = store.dump_all()

    # Second publish of same run
    publisher.publish(dataset=dataset, report=report)
    second_dump = store.dump_all()

    assert len(first_dump["runs"]) == len(second_dump["runs"]) == 1
    assert len(first_dump["source_bank"]) == len(second_dump["source_bank"])
    assert len(first_dump["source_payout"]) == len(second_dump["source_payout"])
    assert len(first_dump["source_ledger"]) == len(second_dump["source_ledger"])


def test_cli_publish_row_counts() -> None:
    """Check 6.7: Row counts per table match report.json exactly."""
    dataset = generate_dataset(n=100, seed=101)
    generator = ReportGenerator()
    report = generator.generate_report(
        dataset=dataset,
        mode="rules_only",
        seed=101,
        seed_set="holdout",
    )

    store = SQLiteStorageAdapter()
    publisher = ReportPublisher(store=store)
    publisher.publish(dataset=dataset, report=report)

    run_id = str(report["run_id"])
    counts = store.count_rows_for_run(run_id)

    assert counts["source_bank"] == len(dataset.bank_txns)
    assert counts["source_payout"] == len(dataset.gateway_payouts)
    assert counts["source_ledger"] == len(dataset.ledger_entries)
    assert counts["runs"] == 1


def test_controls_published() -> None:
    """Check 6.8: control_results populated for all 6 controls."""
    from engine.eval.controls import run_negative_controls

    controls_res = run_negative_controls()
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_only", seed=42)

    store = MemoryStorageAdapter()
    publisher = ReportPublisher(store=store)
    publisher.publish(dataset=dataset, report=report, control_results=controls_res)

    run_id = str(report["run_id"])
    saved_controls = store.get_control_results(run_id)
    assert len(saved_controls) == 6
    expected_controls = [
        "shuffled_truth",
        "null_agent",
        "random_matcher",
        "poisoned_prompt",
        "inverted_rule",
        "disabled_dedup",
    ]
    for ctrl in expected_controls:
        matching = [c for c in saved_controls if c["control_name"] == ctrl]
        assert len(matching) == 1
        assert matching[0]["passed"] is True
