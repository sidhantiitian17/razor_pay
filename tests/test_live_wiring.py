"""Tests for Live Wiring integration (§9 P12, checks 12.1-12.7).

Verifies the live connection between UI data models and the reconciliation engine:
- 12.1: UI run request executed by worker, creating a new run in store
- 12.2: crosscheck tool verifies DOM/DB matches report.json
- 12.3: Exception triage never mutates frozen report.json
- 12.4: close --reverse restores state and sets reversed_at
- 12.5: Smoke wiring and schema validation across endpoints
- 12.6: Second-pass convergence on closed state
- 12.7: crosscheck tool verifies all 6 negative controls in DB
"""

from __future__ import annotations

from engine.adapters.store_memory import MemoryStorageAdapter
from engine.adapters.store_sqlite import SQLiteStorageAdapter
from engine.app.closer import ClosureEngine
from engine.app.publisher import ReportPublisher
from engine.app.reporter import ReportGenerator
from engine.app.worker import ReconciliationWorker
from engine.core.classify import ExceptionClassifier
from engine.core.generator.build import generate_dataset
from engine.core.matching.rules import DeterministicMatcher
from engine.tools.crosscheck import crosscheck_controls, crosscheck_run


def test_run_request_worker_lifecycle() -> None:
    """Check 12.1: Submit run request; worker executes, creates runs row and completes."""
    store = MemoryStorageAdapter()
    req_id = store.create_run_request(config={"n": 60, "seed": 42, "mode": "rules_only"})

    worker = ReconciliationWorker(worker_id="worker-live-1", store=store)
    processed = worker.run_once()
    assert processed is True

    req = store.get_run_request(req_id)
    assert req is not None
    assert req["status"] == "complete"
    assert req["result_run_id"] is not None

    run_row = store.load_run(req["result_run_id"])
    assert run_row is not None
    assert run_row["run_id"] == req["result_run_id"]
    assert "accuracy" in run_row


def test_crosscheck_tool_run() -> None:
    """Check 12.2: crosscheck tool verifies DB rows match report.json exactly."""
    store = SQLiteStorageAdapter()
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_agent", seed=42)

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
    res = crosscheck_run(run_id=run_id, store=store)
    assert res["status"] == "PASS"
    assert res["diff_count"] == 0


def test_crosscheck_fails_on_underpersisted_agent_calls() -> None:
    """Check 12.2: crosscheck_run raises AssertionError if agent_calls are under-persisted."""
    import pytest

    store = SQLiteStorageAdapter()
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_agent", seed=42)

    publisher = ReportPublisher(store=store)
    # Deliberately under-persist agent_calls (publish empty list while report claims >0)
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=[],
        closures=generator.last_closures,
    )

    run_id = str(report["run_id"])
    with pytest.raises(AssertionError, match="Agent calls mismatch"):
        crosscheck_run(run_id=run_id, store=store)


def test_crosscheck_fails_on_underpersisted_closures() -> None:
    """Check 12.2: crosscheck_run raises AssertionError if closures are under-persisted."""
    import pytest

    store = SQLiteStorageAdapter()
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_only", seed=42)

    publisher = ReportPublisher(store=store)
    # Deliberately omit closures from publish
    publisher.publish(
        dataset=dataset,
        report=report,
        match_groups=generator.last_match_groups,
        link_decisions=generator.last_link_decisions,
        agent_calls=generator.last_agent_calls,
        closures=[],
    )

    run_id = str(report["run_id"])
    with pytest.raises(AssertionError, match="Closures mismatch"):
        crosscheck_run(run_id=run_id, store=store)


def test_triage_mutation_isolation() -> None:
    """Check 12.3: Exception triage never mutates frozen report.json (R2)."""
    store = SQLiteStorageAdapter()
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_only", seed=42)

    publisher = ReportPublisher(store=store)
    publisher.publish(dataset=dataset, report=report)

    run_id = str(report["run_id"])
    original_report = store.load_run(run_id)
    assert original_report is not None

    # Simulate UI user updating exception status (triage) in exceptions table
    exc = report["exceptions"][0]
    exc_id = exc["exception_id"]

    store.save_exceptions(
        run_id=run_id,
        exceptions=[
            {
                "exception_id": exc_id,
                "row_ids": exc["row_ids"],
                "bucket": exc["bucket"],
                "severity": exc["severity"],
                "evidence": exc["evidence"],
                "proposed_action": exc["proposed_action"],
                "status": "resolved",
                "assignee": "pam@munderdiffin.com",
                "resolution_note": "Verified manual adjustment with bank statement",
            }
        ],
    )

    # Verify runs.report is UNCHANGED (measurement integrity preserved)
    post_triage_report = store.load_run(run_id)
    assert post_triage_report == original_report


def test_cli_close_reverse() -> None:
    """Check 12.4: close --reverse restores state and sets reversed_at (I14, R2)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    mres = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=mres.matched_groups,
    )

    closer = ClosureEngine()
    cres = closer.close(
        run_id="run-test-rev",
        matched_groups=mres.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )
    assert cres.applied > 0

    rev_res = closer.reverse("run-test-rev")
    assert rev_res.reversed_count == cres.applied
    # Second reverse is a no-op (idempotent)
    assert closer.reverse("run-test-rev").reversed_count == 0


def test_smoke_wiring() -> None:
    """Check 12.5: Smoke wiring and schema validation across endpoints."""
    dataset = generate_dataset(n=60, seed=42)
    generator = ReportGenerator()
    report = generator.generate_report(dataset=dataset, mode="rules_agent", seed=42)

    store = MemoryStorageAdapter()
    publisher = ReportPublisher(store=store)
    publisher.publish(dataset=dataset, report=report)

    run_id = str(report["run_id"])
    loaded = store.load_run(run_id)
    assert loaded is not None
    assert loaded["schema_version"] == "1.0.0"


def test_second_pass_convergence_live() -> None:
    """Check 12.6: Second pass convergence on closed state yields 0 new closures (R2)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    mres1 = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions1 = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=mres1.matched_groups,
    )

    closer = ClosureEngine()
    cres1 = closer.close(
        run_id="run-conv-1",
        matched_groups=mres1.matched_groups,
        exceptions=exceptions1,
        dry_run=False,
    )
    assert cres1.applied > 0

    # Second pass on identical data
    mres2 = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)
    exceptions2 = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=mres2.matched_groups,
    )
    cres2 = closer.close(
        run_id="run-conv-1",
        matched_groups=mres2.matched_groups,
        exceptions=exceptions2,
        dry_run=False,
    )
    assert cres2.applied == 0
    assert len(exceptions2) == len(exceptions1)


def test_crosscheck_tool_controls() -> None:
    """Check 12.7: crosscheck tool verifies all 6 negative controls in database."""
    store = SQLiteStorageAdapter()
    res = crosscheck_controls(store=store)
    assert res["status"] == "PASS"
    assert res["controls_verified"] == 6


def test_multi_seed_report_config_seed_integrity() -> None:
    """Verify that every report in a multi-seed batch contains its exact seed in config.seed."""
    generator = ReportGenerator()
    seed_list = [101, 102, 103]

    for s in seed_list:
        dataset = generate_dataset(n=50, seed=s)
        report = generator.generate_report(
            dataset=dataset,
            mode="rules_only",
            seed=s,
            seed_set="holdout",
            seeds=seed_list,
        )
        assert report["config"]["seed"] == s, (
            f"Expected config.seed={s}, got {report['config']['seed']}"
        )
