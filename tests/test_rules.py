"""Tests for deterministic matcher rule stack (checks 2.3-2.7, D1, D2, D23)."""

from datetime import UTC, date, datetime

from engine.core.generator.build import generate_dataset
from engine.core.matching.rules import DeterministicMatcher
from engine.core.models import (
    BankTxn,
    CohortName,
    ExceptionBucket,
    GatewayPayout,
    LedgerEntry,
    ResolvedTag,
)


def test_zero_false_positives() -> None:
    """Check 2.3: Zero false positive links across seeds 1..20 (D23)."""
    matcher = DeterministicMatcher()
    for seed in range(1, 21):
        dataset = generate_dataset(n=60, seed=seed)
        result = matcher.match(
            dataset.bank_txns,
            dataset.gateway_payouts,
            dataset.ledger_entries,
        )

        truth_link_pairs = {
            (t.link_type, t.left_id, t.right_id): t.is_match for t in dataset.truth_links
        }

        for link in result.predicted_links:
            key = (link.link_type, link.left_id, link.right_id)
            # If predicted as a match, truth link must be True
            if link.is_match:
                assert truth_link_pairs.get(key, False) is True, f"FP on seed {seed}: {key}"


def test_clean_recall() -> None:
    """Check 2.4: >= 98% of clean cohort matched by rules alone."""
    matcher = DeterministicMatcher()
    clean_total = 0
    clean_matched = 0

    for seed in range(1, 11):
        dataset = generate_dataset(n=100, seed=seed)
        clean_groups = [g for g in dataset.truth_groups if g.cohort == CohortName.CLEAN]
        clean_total += len(clean_groups)

        result = matcher.match(
            dataset.bank_txns,
            dataset.gateway_payouts,
            dataset.ledger_entries,
        )

        # Matched clean groups
        matched_group_bank_ids = {
            g.bank_ids[0]
            for g in result.matched_groups
            if g.tag == ResolvedTag.CLEAN and g.bank_ids
        }

        for g in clean_groups:
            if g.bank_ids[0] in matched_group_bank_ids:
                clean_matched += 1

    assert clean_total > 0
    recall = clean_matched / clean_total
    assert recall >= 0.98, f"Clean recall too low: {recall:.3f}"


def test_duplicates() -> None:
    """Check 2.5: 100% of duplicate payouts flagged as exceptions, never matched 1:1."""
    matcher = DeterministicMatcher()
    dataset = generate_dataset(n=100, seed=42)
    result = matcher.match(
        dataset.bank_txns,
        dataset.gateway_payouts,
        dataset.ledger_entries,
    )

    dup_groups = [g for g in dataset.truth_groups if g.cohort == CohortName.DUPLICATE_PAYOUT]
    assert len(dup_groups) > 0

    # Collect row IDs in duplicate exceptions
    duplicate_exception_rows: set[str] = set()
    for exc in result.exceptions:
        if exc.bucket == ExceptionBucket.DUPLICATE:
            duplicate_exception_rows.update(exc.row_ids)

    for g in dup_groups:
        for p_id in g.payout_ids:
            assert p_id in duplicate_exception_rows, f"Dup {p_id} not flagged in exceptions"


def test_refund_pairs() -> None:
    """Check 2.6: Refund pairs grouped; each journal set sums to 0."""
    matcher = DeterministicMatcher()
    dataset = generate_dataset(n=100, seed=42)
    result = matcher.match(
        dataset.bank_txns,
        dataset.gateway_payouts,
        dataset.ledger_entries,
    )

    refund_matches = [g for g in result.matched_groups if g.tag == ResolvedTag.REFUND]
    assert len(refund_matches) > 0

    for g in refund_matches:
        ledgers = [dataset.ledger_by_id[lid] for lid in g.ledger_ids]
        assert sum(e.amount_paise for e in ledgers) == 0


def test_tolerance_boundaries() -> None:
    """Check 2.7: 49p matches, 50p matches, 51p does not; 2d matches, 3d does not (D1, D2)."""
    matcher = DeterministicMatcher()

    base_dt = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    base_date = date(2026, 8, 1)

    payout = GatewayPayout(
        payout_id="pout_SYNTH00000001",
        created_at=base_dt,
        settled_at=base_dt,
        amount_paise=100000,
        fee_paise=2000,
        tax_paise=360,
        utr="SYNTH0000000000000001",
        status="processed",
    )
    net = payout.net_paise  # 97640

    ledgers = [
        LedgerEntry(
            ledger_id="LED-000001",
            journal_id="JRN-000001",
            entry_date=base_date,
            amount_paise=-100000,
            account="settlements_receivable",
            reference=payout.payout_id,
        ),
        LedgerEntry(
            ledger_id="LED-000002",
            journal_id="JRN-000001",
            entry_date=base_date,
            amount_paise=net,
            account="bank",
            reference=payout.payout_id,
        ),
        LedgerEntry(
            ledger_id="LED-000003",
            journal_id="JRN-000001",
            entry_date=base_date,
            amount_paise=2000,
            account="gateway_fees",
            reference=payout.payout_id,
        ),
        LedgerEntry(
            ledger_id="LED-000004",
            journal_id="JRN-000001",
            entry_date=base_date,
            amount_paise=360,
            account="gateway_tax",
            reference=payout.payout_id,
        ),
    ]

    # Test 49p drift: should match
    bank_49p = BankTxn(
        bank_id="BNK-000001",
        posted_at=base_dt,
        value_date=base_date,
        amount_paise=net + 49,
        utr=payout.utr,
        narration="SETTLEMENT",
    )
    res_49p = matcher.match([bank_49p], [payout], ledgers)
    assert len(res_49p.matched_groups) == 1
    assert res_49p.matched_groups[0].tag == ResolvedTag.DRIFT

    # Test 50p drift: within boundary tolerance (<= 50p) -> should match
    bank_50p = BankTxn(
        bank_id="BNK-000002",
        posted_at=base_dt,
        value_date=base_date,
        amount_paise=net + 50,
        utr=payout.utr,
        narration="SETTLEMENT",
    )
    res_50p = matcher.match([bank_50p], [payout], ledgers)
    assert len(res_50p.matched_groups) == 1

    # Test 51p drift: exceeds tolerance -> should NOT match as resolved drift
    bank_51p = BankTxn(
        bank_id="BNK-000003",
        posted_at=base_dt,
        value_date=base_date,
        amount_paise=net + 51,
        utr=payout.utr,
        narration="SETTLEMENT",
    )
    res_51p = matcher.match([bank_51p], [payout], ledgers)
    assert len(res_51p.matched_groups) == 0

    # Test 2 days skew: should match as timing_tolerated
    bank_2d = BankTxn(
        bank_id="BNK-000004",
        posted_at=base_dt,
        value_date=date(2026, 8, 3),
        amount_paise=net,
        utr=payout.utr,
        narration="SETTLEMENT",
    )
    res_2d = matcher.match([bank_2d], [payout], ledgers)
    assert len(res_2d.matched_groups) == 1
    assert res_2d.matched_groups[0].tag == ResolvedTag.TIMING_TOLERATED

    # Test 3 days skew: should NOT match
    bank_3d = BankTxn(
        bank_id="BNK-000005",
        posted_at=base_dt,
        value_date=date(2026, 8, 4),
        amount_paise=net,
        utr=payout.utr,
        narration="SETTLEMENT",
    )
    res_3d = matcher.match([bank_3d], [payout], ledgers)
    assert len(res_3d.matched_groups) == 0
