"""Tests for idempotent ledger closer, dry run, reversal, and invariants (P4)."""

from engine.app.closer import ClosureEngine
from engine.core.classify import ExceptionClassifier
from engine.core.generator.build import generate_dataset
from engine.core.matching.rules import DeterministicMatcher


def test_idempotent() -> None:
    """Check 4.6: Applying same run twice yields one closure set; second is no-op (R2)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    closer = ClosureEngine()
    run_id = "run_test_idempotent"

    # First apply
    result1 = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )
    assert result1.applied > 0
    assert result1.dry_run is False

    # Second apply on the same closer / run_id
    result2 = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )
    assert result2.applied == 0
    assert result2.already_closed == result1.applied


def test_dry_run() -> None:
    """Check 4.7: --dry-run writes zero rows and still reports what it would write (R2)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    closer = ClosureEngine()
    run_id = "run_test_dry_run"

    dry_result = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=True,
    )

    assert dry_result.dry_run is True
    assert dry_result.applied == 0
    assert dry_result.planned > 0
    # Assert no persisted state was created
    assert closer.get_closure_count(run_id) == 0


def test_reversal() -> None:
    """Check 4.8: I14 — close --reverse <run_id> restores every before state exactly (R2)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    closer = ClosureEngine()
    run_id = "run_test_reversal"

    # Capture initial states
    initial_states = closer.capture_system_state(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
    )

    # Apply closures
    apply_result = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )
    assert apply_result.applied > 0

    # Reverse closures
    reversal_result = closer.reverse(run_id)
    assert reversal_result.reversed_count == apply_result.applied

    # Check restored state
    restored_states = closer.capture_system_state(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
    )
    assert restored_states == initial_states


def test_only_resolved() -> None:
    """Check 4.9: I15 — no closure for a row in an open exception (R2, R9)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    closer = ClosureEngine()
    run_id = "run_test_only_resolved"

    result = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )

    exception_row_ids = {row_id for ex in exceptions for row_id in ex.row_ids}
    closed_row_ids = result.closed_row_ids

    # Intersection must be empty (I15)
    overlap = exception_row_ids.intersection(closed_row_ids)
    assert len(overlap) == 0, f"Found closed rows that belong to open exceptions: {overlap}"


def test_second_pass() -> None:
    """Check 4.10: Second pass after close yields second_pass_new_closures == 0 (R2)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    closer = ClosureEngine()
    run_id = "run_test_second_pass"

    first_pass = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )

    second_pass = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )

    assert second_pass.second_pass_new_closures == 0
    assert first_pass.applied > 0


def test_balanced() -> None:
    """Check 4.11: Every adjustment journal sums to 0 (§3.3)."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    closer = ClosureEngine()
    run_id = "run_test_balanced"

    result = closer.close(
        run_id=run_id,
        matched_groups=match_result.matched_groups,
        exceptions=exceptions,
        dry_run=False,
    )

    for jrn in result.adjustment_journals:
        assert sum(entry.amount_paise for entry in jrn.entries) == 0
