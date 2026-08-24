"""Tests for frozen models (I2, I4, I8) — check 0.3."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from engine.core.models import (
    BankTxn,
    Closure,
    ExceptionBucket,
    GatewayPayout,
    GroupKind,
    LedgerEntry,
    ReconException,
    ResolvedTag,
    TruthGroup,
    validate_group_cardinality,
)
from pydantic import ValidationError


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TestBankTxn:
    """BankTxn model tests."""

    def test_create_valid(self) -> None:
        txn = BankTxn(
            bank_id="BNK-000001",
            posted_at=_utc_now(),
            value_date=date.today(),
            amount_paise=12500,
            utr="SYNTH0000000000000001",
            narration="Settlement credit",
        )
        assert txn.amount_paise == 12500
        assert txn.currency == "INR"

    def test_frozen_raises(self) -> None:
        txn = BankTxn(
            bank_id="BNK-000001",
            posted_at=_utc_now(),
            value_date=date.today(),
            amount_paise=12500,
            utr=None,
            narration="test",
        )
        with pytest.raises(ValidationError):
            txn.amount_paise = 99999  # type: ignore[misc]

    def test_float_paise_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Float not allowed"):
            BankTxn(
                bank_id="BNK-000001",
                posted_at=_utc_now(),
                value_date=date.today(),
                amount_paise=125.00,  # type: ignore[arg-type]
                utr=None,
                narration="test",
            )

    def test_naive_datetime_rejected(self) -> None:
        """I2: all datetimes tz-aware UTC."""
        with pytest.raises(ValidationError, match="Naive datetime"):
            BankTxn(
                bank_id="BNK-000001",
                posted_at=datetime(2026, 1, 1),  # naive!
                value_date=date.today(),
                amount_paise=12500,
                utr=None,
                narration="test",
            )


class TestGatewayPayout:
    """GatewayPayout model tests — I4: net = gross - fee - tax."""

    def test_net_paise(self) -> None:
        payout = GatewayPayout(
            payout_id="pout_SYNTH00000001",
            created_at=_utc_now(),
            settled_at=_utc_now(),
            amount_paise=10000,  # gross
            fee_paise=200,
            tax_paise=36,
            utr="SYNTH0000000000000001",
            status="processed",
        )
        assert payout.net_paise == 10000 - 200 - 36
        assert payout.net_paise == 9764

    def test_frozen(self) -> None:
        payout = GatewayPayout(
            payout_id="pout_SYNTH00000001",
            created_at=_utc_now(),
            settled_at=None,
            amount_paise=10000,
            fee_paise=200,
            tax_paise=36,
            utr=None,
            status="processed",
        )
        with pytest.raises(ValidationError):
            payout.amount_paise = 5000  # type: ignore[misc]

    def test_float_fee_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Float not allowed"):
            GatewayPayout(
                payout_id="pout_SYNTH00000001",
                created_at=_utc_now(),
                settled_at=None,
                amount_paise=10000,
                fee_paise=200.0,  # type: ignore[arg-type]
                tax_paise=36,
                utr=None,
                status="processed",
            )


class TestLedgerEntry:
    """LedgerEntry model tests."""

    def test_signed_amount(self) -> None:
        entry = LedgerEntry(
            ledger_id="LED-000001",
            journal_id="JRN-000001",
            entry_date=date.today(),
            amount_paise=-10000,
            account="settlements_receivable",
            reference="pout_SYNTH00000001",
        )
        assert entry.amount_paise == -10000


class TestTruthGroup:
    """TruthGroup model tests."""

    def test_create(self) -> None:
        tg = TruthGroup(
            group_id="TG-0001",
            kind=GroupKind.SIMPLE,
            cohort="clean",
            bank_ids=["BNK-000001"],
            payout_ids=["pout_SYNTH00000001"],
            ledger_ids=["LED-001", "LED-002", "LED-003", "LED-004"],
            expected_outcome="resolved",
            expected_tag=ResolvedTag.CLEAN,
        )
        assert tg.expected_outcome == "resolved"
        assert tg.expected_bucket is None


class TestGroupKindCardinality:
    """I8: group kind cardinality invariants."""

    def test_simple_valid(self) -> None:
        assert validate_group_cardinality(GroupKind.SIMPLE, 1, 1, 4)

    def test_simple_wrong_bank(self) -> None:
        with pytest.raises(ValueError, match="bank_count must be 1"):
            validate_group_cardinality(GroupKind.SIMPLE, 2, 1, 4)

    def test_duplicate_set_valid(self) -> None:
        assert validate_group_cardinality(GroupKind.DUPLICATE_SET, 1, 2, 4)

    def test_refund_pair_zero_bank(self) -> None:
        assert validate_group_cardinality(GroupKind.REFUND_PAIR, 0, 1, 8)

    def test_refund_pair_one_bank(self) -> None:
        assert validate_group_cardinality(GroupKind.REFUND_PAIR, 1, 1, 8)

    def test_orphan_bank_valid(self) -> None:
        assert validate_group_cardinality(GroupKind.ORPHAN_BANK, 1, 0, 0)

    def test_orphan_ledger_valid(self) -> None:
        assert validate_group_cardinality(GroupKind.ORPHAN_LEDGER, 0, 0, 4)

    def test_orphan_ledger_no_ledger(self) -> None:
        with pytest.raises(ValueError, match="ledger_count must be >= 1"):
            validate_group_cardinality(GroupKind.ORPHAN_LEDGER, 0, 0, 0)


class TestReconException:
    """ReconException model tests."""

    def test_evidence_required(self) -> None:
        exc = ReconException(
            exception_id="EX-0001",
            row_ids=["BNK-000007"],
            bucket=ExceptionBucket.ORPHAN_BANK,
            severity="high",
            evidence=["bank.amount_paise=12500", "no payout within +/-7d"],
            proposed_action="Trace credit with bank",
        )
        assert len(exc.evidence) >= 2


class TestClosure:
    """Closure model tests."""

    def test_utc_required(self) -> None:
        """applied_at must be tz-aware UTC."""
        with pytest.raises(ValidationError, match="Naive datetime"):
            Closure(
                closure_id="CL-001",
                run_id="test-run",
                target="payout:pout_SYNTH00000001",
                action="mark_reconciled",
                before={"status": "pending"},
                after={"status": "reconciled"},
                applied_at=datetime(2026, 1, 1),  # naive
            )
