"""Tests for outlier attribution logic (check 2.8, §3.4)."""

from datetime import UTC, date, datetime

from engine.core.matching.attribute import attribute_triad_outlier
from engine.core.models import (
    BankTxn,
    ExceptionBucket,
    GatewayPayout,
    LedgerEntry,
    ResolvedTag,
)


def _make_fixture(
    bank_paise: int,
    gross_paise: int,
    fee_paise: int,
    tax_paise: int,
    ledger_bank_paise: int,
    ledger_rec_paise: int,
) -> tuple[BankTxn, GatewayPayout, list[LedgerEntry]]:
    dt = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    d = date(2026, 8, 1)

    bank = BankTxn(
        bank_id="BNK-000001",
        posted_at=dt,
        value_date=d,
        amount_paise=bank_paise,
        utr="SYNTH0000000000000001",
        narration="SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id="pout_SYNTH00000001",
        created_at=dt,
        settled_at=dt,
        amount_paise=gross_paise,
        fee_paise=fee_paise,
        tax_paise=tax_paise,
        utr="SYNTH0000000000000001",
        status="processed",
    )
    ledgers = [
        LedgerEntry(
            ledger_id="LED-000001",
            journal_id="JRN-000001",
            entry_date=d,
            amount_paise=-ledger_rec_paise,
            account="settlements_receivable",
            reference=payout.payout_id,
        ),
        LedgerEntry(
            ledger_id="LED-000002",
            journal_id="JRN-000001",
            entry_date=d,
            amount_paise=ledger_bank_paise,
            account="bank",
            reference=payout.payout_id,
        ),
        LedgerEntry(
            ledger_id="LED-000003",
            journal_id="JRN-000001",
            entry_date=d,
            amount_paise=fee_paise,
            account="gateway_fees",
            reference=payout.payout_id,
        ),
        LedgerEntry(
            ledger_id="LED-000004",
            journal_id="JRN-000001",
            entry_date=d,
            amount_paise=tax_paise,
            account="gateway_tax",
            reference=payout.payout_id,
        ),
    ]
    return bank, payout, ledgers


def test_outlier_table_row1_clean() -> None:
    """Row 1: A, A, A, agree -> resolved clean."""
    bank, payout, ledgers = _make_fixture(
        bank_paise=97640,
        gross_paise=100000,
        fee_paise=2000,
        tax_paise=360,
        ledger_bank_paise=97640,
        ledger_rec_paise=100000,
    )
    verdict, tag, bucket = attribute_triad_outlier(bank, payout, ledgers)
    assert verdict == "resolved"
    assert tag == ResolvedTag.CLEAN
    assert bucket is None


def test_outlier_table_row2_drift() -> None:
    """Row 2: A±d (d<=49), A, A, agree -> resolved drift."""
    bank, payout, ledgers = _make_fixture(
        bank_paise=97640 + 35,
        gross_paise=100000,
        fee_paise=2000,
        tax_paise=360,
        ledger_bank_paise=97640,
        ledger_rec_paise=100000,
    )
    verdict, tag, bucket = attribute_triad_outlier(bank, payout, ledgers)
    assert verdict == "resolved"
    assert tag == ResolvedTag.DRIFT
    assert bucket is None


def test_outlier_table_row3_amount_mismatch() -> None:
    """Row 3: A±d (d>=80), A, A, agree -> amount_mismatch (bank outlier)."""
    bank, payout, ledgers = _make_fixture(
        bank_paise=97640 + 150,
        gross_paise=100000,
        fee_paise=2000,
        tax_paise=360,
        ledger_bank_paise=97640,
        ledger_rec_paise=100000,
    )
    verdict, tag, bucket = attribute_triad_outlier(bank, payout, ledgers)
    assert verdict == "unresolved"
    assert tag is None
    assert bucket == ExceptionBucket.AMOUNT_MISMATCH


def test_outlier_table_row4_fee_mismatch() -> None:
    """Row 4: A, A±d, A, agree -> fee_mismatch (payout fee outlier)."""
    # Payout has fee perturbed so net is 97140 instead of 97640
    bank, payout, ledgers = _make_fixture(
        bank_paise=97640,
        gross_paise=100000,
        fee_paise=2500,
        tax_paise=360,
        ledger_bank_paise=97640,
        ledger_rec_paise=100000,
    )
    verdict, tag, bucket = attribute_triad_outlier(bank, payout, ledgers)
    assert verdict == "unresolved"
    assert tag is None
    assert bucket == ExceptionBucket.FEE_MISMATCH


def test_outlier_table_row5_ledger_break() -> None:
    """Row 5: A, A, A±d, disagree -> partial_group."""
    bank, payout, ledgers = _make_fixture(
        bank_paise=97640,
        gross_paise=100000,
        fee_paise=2000,
        tax_paise=360,
        ledger_bank_paise=95000,
        ledger_rec_paise=98000,
    )
    verdict, tag, bucket = attribute_triad_outlier(bank, payout, ledgers)
    assert verdict == "unresolved"
    assert tag is None
    assert bucket == ExceptionBucket.PARTIAL_GROUP
