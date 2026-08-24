"""Tests for the candidate space blocker (check 2.1, 2.2, §4.2)."""

from engine.core.generator.build import generate_dataset
from engine.core.matching.blocker import build_candidate_space, evaluate_blocker_recall


def test_recall() -> None:
    """Check 2.1: blocker_recall == 1.0 on seeds 1..20 (§4.2 — caps the whole system)."""
    for seed in range(1, 21):
        dataset = generate_dataset(n=60, seed=seed)
        space = build_candidate_space(
            dataset.bank_txns,
            dataset.gateway_payouts,
            dataset.ledger_entries,
        )
        recall = evaluate_blocker_recall(space, dataset.truth_links)
        msg = f"Seed {seed} dropped links: {recall.numerator}/{recall.denominator}"
        assert recall.value == 1.0, msg


def test_space_size() -> None:
    """Check 2.2: |C| is recorded and < n^2 / 4 (blocking actually blocks)."""
    n = 100
    dataset = generate_dataset(n=n, seed=42)
    space = build_candidate_space(
        dataset.bank_txns,
        dataset.gateway_payouts,
        dataset.ledger_entries,
    )

    # Cross product size: len(bank) * len(payout) + len(payout) * len(ledger)
    total_cross = len(dataset.bank_txns) * len(dataset.gateway_payouts) + len(
        dataset.gateway_payouts
    ) * len(dataset.ledger_entries)

    assert space.size > 0
    assert space.size < (total_cross / 4)
