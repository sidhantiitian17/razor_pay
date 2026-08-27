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
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=generator.last_closures,
    )

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
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=generator.last_closures,
    )

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
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=generator.last_closures,
    )
    first_dump = store.dump_all()

    # Second publish of same run
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=generator.last_closures,
    )
    second_dump = store.dump_all()

    assert len(first_dump["runs"]) == len(second_dump["runs"]) == 1
    assert len(first_dump["source_bank"]) == len(second_dump["source_bank"])
    assert len(first_dump["source_payout"]) == len(second_dump["source_payout"])
    assert len(first_dump["source_ledger"]) == len(second_dump["source_ledger"])
    assert len(first_dump["match_groups"]) == len(second_dump["match_groups"])
    assert len(first_dump["agent_calls"]) == len(second_dump["agent_calls"])
    assert len(first_dump["closures"]) == len(second_dump["closures"])


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
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=generator.last_closures,
    )

    run_id = str(report["run_id"])
    counts = store.count_rows_for_run(run_id)

    assert counts["source_bank"] == len(dataset.bank_txns)
    assert counts["source_payout"] == len(dataset.gateway_payouts)
    assert counts["source_ledger"] == len(dataset.ledger_entries)
    assert counts["truth_groups"] == len(dataset.truth_groups)
    assert counts["match_groups"] == len(generator.last_match_groups)
    assert counts["link_decisions"] == len(generator.last_link_decisions)
    assert counts["exceptions"] == len(report.get("exceptions", []))
    assert counts["agent_calls"] == 0  # rules_only mode has 0 agent calls
    assert counts["closures"] == len(generator.last_closures)
    assert counts["runs"] == 1


def test_rules_agent_db_persistence_matches_telemetry() -> None:
    """Check 6.7 & P6: rules_agent persisted agent_calls match reported llm_calls & cost."""
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_agent", seed=42)

    store = SQLiteStorageAdapter()
    publisher = ReportPublisher(store=store)
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=generator.last_closures,
    )

    run_id = str(report["run_id"])
    counts = store.count_rows_for_run(run_id)
    reported_llm_calls = report["throughput"]["llm_calls"]

    assert reported_llm_calls > 0
    assert counts["agent_calls"] == reported_llm_calls
    assert counts["match_groups"] == len(generator.last_match_groups)
    assert counts["link_decisions"] == len(generator.last_link_decisions)
    assert counts["closures"] == len(generator.last_closures)

    dump = store.dump_all()
    run_agent_calls = [c for c in dump["agent_calls"] if c["run_id"] == run_id]
    assert len(run_agent_calls) == reported_llm_calls
    total_db_cost = sum(float(c["cost_usd"]) for c in run_agent_calls)
    assert round(total_db_cost, 4) == round(float(report["cost"]["cost_usd"]), 4)


def test_controls_published() -> None:
    """Check 6.8: control_results populated with authentic computed values for all 6 controls."""
    from engine.eval.controls import run_negative_controls

    controls_res = run_negative_controls()
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_only", seed=42)

    store = MemoryStorageAdapter()
    publisher = ReportPublisher(store=store)
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=generator.last_closures,
        control_results=controls_res,
    )

    run_id = str(report["run_id"])
    saved_controls = store.get_control_results(run_id)
    assert len(saved_controls) == 6
    control_map = {c["control_name"]: c for c in saved_controls}

    # 1. shuffled_truth: precision collapses to < 0.05
    assert control_map["shuffled_truth"]["passed"] is True
    assert control_map["shuffled_truth"]["details"]["observed_match_rate"] < 0.05

    # 2. null_agent: zero side effects on deterministic rules
    assert control_map["null_agent"]["passed"] is True
    assert control_map["null_agent"]["details"]["identical_to_rules_only"] is True

    # 3. random_matcher: chance floor precision < 0.35
    assert control_map["random_matcher"]["passed"] is True
    assert control_map["random_matcher"]["details"]["observed_precision"] < 0.35

    # 4. poisoned_prompt: truth leak detector fires
    assert control_map["poisoned_prompt"]["passed"] is True
    assert control_map["poisoned_prompt"]["details"]["leak_detector_fired"] is True

    # 5. inverted_rule: broken test assertions >= 5
    assert control_map["inverted_rule"]["passed"] is True
    assert control_map["inverted_rule"]["details"]["tests_failed"] >= 5

    # 6. disabled_dedup: duplicate bucket emptied to 0
    assert control_map["disabled_dedup"]["passed"] is True
    assert control_map["disabled_dedup"]["details"]["duplicate_bucket_size"] == 0
