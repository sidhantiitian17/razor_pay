"""Tests for reconciliation metrics, rates sum, and invariants (check 2.10, I9, I10, D5)."""

from engine.core.generator.build import generate_dataset
from engine.core.matching.rules import DeterministicMatcher
from engine.core.metrics import compute_reconciliation_metrics


def test_rates_sum() -> None:
    """I9 + I10: rates sum to 1.0; each row in exactly one terminal state (D5)."""
    matcher = DeterministicMatcher()

    for seed in (42, 101, 102):
        dataset = generate_dataset(n=100, seed=seed)
        result = matcher.match(
            dataset.bank_txns,
            dataset.gateway_payouts,
            dataset.ledger_entries,
        )

        metrics = compute_reconciliation_metrics(
            bank_txns=dataset.bank_txns,
            gateway_payouts=dataset.gateway_payouts,
            ledger_entries=dataset.ledger_entries,
            matched_groups=result.matched_groups,
            exceptions=result.exceptions,
            truth_groups=dataset.truth_groups,
            candidate_space_size=1000,
        )

        # I9: resolved_rate + unresolved_rate == 1.0
        assert round(metrics.resolved_rate.value + metrics.unresolved_rate.value, 6) == 1.0
        assert metrics.resolved_rate.denominator == metrics.unresolved_rate.denominator

        # I10: Every row ID in exactly one terminal state
        resolved_rows = {
            rid for g in result.matched_groups for rid in g.bank_ids + g.payout_ids + g.ledger_ids
        }
        unresolved_rows = {rid for e in result.exceptions for rid in e.row_ids}

        # Zero overlap
        assert resolved_rows.isdisjoint(unresolved_rows)

        total_source_rows = (
            len(dataset.bank_txns) + len(dataset.gateway_payouts) + len(dataset.ledger_entries)
        )
        assert len(resolved_rows) + len(unresolved_rows) == total_source_rows
