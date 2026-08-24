"""Tests for cohort injectors, disjointness, and attribution (I6, I7, D1, D2, D3)."""

from engine.core.generator.build import generate_dataset
from engine.core.generator.cohorts import COHORT_INJECTORS, COHORT_TERMINAL_MAP
from engine.core.models import (
    CohortName,
    ExceptionBucket,
    ResolvedTag,
)


def test_terminal_states() -> None:
    """I6 — every cohort maps to exactly one terminal state (R6)."""
    assert len(COHORT_TERMINAL_MAP) == 13
    assert set(COHORT_TERMINAL_MAP.keys()) == set(CohortName)

    for _cohort, (outcome, tag, bucket) in COHORT_TERMINAL_MAP.items():
        if outcome == "resolved":
            assert tag is not None and isinstance(tag, ResolvedTag)
            assert bucket is None
        else:
            assert outcome == "unresolved"
            assert tag is None
            assert bucket is not None and isinstance(bucket, ExceptionBucket)


def test_all_cohort_injectors_registered() -> None:
    """All 13 cohorts must have registered injector functions."""
    assert len(COHORT_INJECTORS) == 13
    assert set(COHORT_INJECTORS.keys()) == set(CohortName)


def test_disjoint() -> None:
    """I7 — no cohort's records satisfy another's predicate (D1, D2)."""
    dataset = generate_dataset(n=100, seed=42)

    # Group records by truth group cohort
    for group in dataset.truth_groups:
        cohort = group.cohort
        outcome, tag, bucket = COHORT_TERMINAL_MAP[cohort]
        assert group.expected_outcome == outcome
        assert group.expected_tag == tag
        assert group.expected_bucket == bucket

        # Check disjointness properties for specific cohorts
        if cohort == CohortName.CLEAN:
            # Bank matches payout net, dates align, UTR matches
            assert len(group.bank_ids) == 1 and len(group.payout_ids) == 1
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            assert b.amount_paise == p.net_paise
            assert b.utr == p.utr
            assert b.value_date == p.settled_at.date()  # type: ignore[union-attr]

        elif cohort == CohortName.DRIFT_TOLERATED:
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            drift = abs(b.amount_paise - p.net_paise)
            assert 1 <= drift <= 49

        elif cohort == CohortName.DRIFT_EXCEPTION:
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            drift = abs(b.amount_paise - p.net_paise)
            assert 80 <= drift <= 200

        elif cohort == CohortName.SKEW_TOLERATED:
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            days = abs((b.value_date - p.settled_at.date()).days)  # type: ignore[union-attr]
            assert 1 <= days <= 2

        elif cohort == CohortName.SKEW_EXCEPTION:
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            days = abs((b.value_date - p.settled_at.date()).days)  # type: ignore[union-attr]
            assert 3 <= days <= 5

        elif cohort == CohortName.MISSING_UTR_RECOVERABLE:
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            assert (b.utr is None or p.utr is None) and (b.utr != p.utr)
            assert p.payout_id in b.narration

        elif cohort == CohortName.MISSING_UTR_UNRECOVERABLE:
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            assert b.utr is None and p.utr is None
            assert p.payout_id not in b.narration

        elif cohort == CohortName.DUPLICATE_PAYOUT:
            assert len(group.payout_ids) == 2
            p1 = dataset.payout_by_id[group.payout_ids[0]]
            p2 = dataset.payout_by_id[group.payout_ids[1]]
            assert p1.utr == p2.utr
            assert p1.amount_paise == p2.amount_paise

        elif cohort == CohortName.REFUND_PAIR:
            assert len(group.ledger_ids) == 8

        elif cohort == CohortName.REFUND_UNPAIRED:
            assert len(group.bank_ids) == 0 and len(group.payout_ids) == 0

        elif cohort == CohortName.FEE_MISMATCH:
            b = dataset.bank_by_id[group.bank_ids[0]]
            p = dataset.payout_by_id[group.payout_ids[0]]
            # Payout fee was altered, gross unchanged, so net differs from bank
            assert b.amount_paise != p.net_paise

        elif cohort == CohortName.ORPHAN_BANK:
            assert len(group.payout_ids) == 0 and len(group.ledger_ids) == 0

        elif cohort == CohortName.ORPHAN_LEDGER:
            assert len(group.bank_ids) == 0 and len(group.payout_ids) == 0


def test_attribution() -> None:
    """§3.4 outlier table holds per cohort — amount and fee mismatches separable (D3)."""
    dataset = generate_dataset(n=100, seed=42)

    # For drift_exception (amount_mismatch): bank is the outlier
    drift_groups = [g for g in dataset.truth_groups if g.cohort == CohortName.DRIFT_EXCEPTION]
    assert len(drift_groups) > 0
    for g in drift_groups:
        b = dataset.bank_by_id[g.bank_ids[0]]
        p = dataset.payout_by_id[g.payout_ids[0]]
        ledgers = [dataset.ledger_by_id[lid] for lid in g.ledger_ids]
        bank_ledger = next(entry for entry in ledgers if entry.account == "bank")
        rec_ledger = next(entry for entry in ledgers if entry.account == "settlements_receivable")

        # Bank amount != payout net
        assert b.amount_paise != p.net_paise
        # Ledger receivable balances payout gross
        assert abs(rec_ledger.amount_paise) == p.amount_paise
        # Ledger bank entry matches expected payout net (so bank statement is the outlier)
        assert bank_ledger.amount_paise == p.net_paise

    # For fee_mismatch: payout fee is the outlier
    fee_groups = [g for g in dataset.truth_groups if g.cohort == CohortName.FEE_MISMATCH]
    assert len(fee_groups) > 0
    for g in fee_groups:
        b = dataset.bank_by_id[g.bank_ids[0]]
        p = dataset.payout_by_id[g.payout_ids[0]]
        ledgers = [dataset.ledger_by_id[lid] for lid in g.ledger_ids]
        fee_ledger = next(entry for entry in ledgers if entry.account == "gateway_fees")
        rec_ledger = next(entry for entry in ledgers if entry.account == "settlements_receivable")

        # Gross matches ledger receivable
        assert abs(rec_ledger.amount_paise) == p.amount_paise
        # Payout fee does not match ledger fee
        assert p.fee_paise != fee_ledger.amount_paise
        # Bank amount matches ledger bank entry
        bank_ledger = next(entry for entry in ledgers if entry.account == "bank")
        assert b.amount_paise == bank_ledger.amount_paise
