"""Tests for guardrail validation and safety filters (check 3.7, §3.6, R8, D15)."""

from datetime import UTC, date, datetime

from engine.core.guardrail import (
    GuardrailConfig,
    GuardrailValidator,
    MatchProposal,
)
from engine.core.models import BankTxn, GatewayPayout, LedgerEntry


def _make_sample_data() -> tuple[BankTxn, GatewayPayout, list[LedgerEntry]]:
    dt = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    d = date(2026, 8, 1)

    bank = BankTxn(
        bank_id="BNK-000001",
        posted_at=dt,
        value_date=d,
        amount_paise=97640,
        utr="SYNTH0000000000000001",
        narration="SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id="pout_SYNTH00000001",
        created_at=dt,
        settled_at=dt,
        amount_paise=100000,
        fee_paise=2000,
        tax_paise=360,
        utr="SYNTH0000000000000001",
        status="processed",
    )
    ledgers = [
        LedgerEntry(
            ledger_id="LED-000001",
            journal_id="JRN-000001",
            entry_date=d,
            amount_paise=-100000,
            account="settlements_receivable",
            reference=payout.payout_id,
        ),
        LedgerEntry(
            ledger_id="LED-000002",
            journal_id="JRN-000001",
            entry_date=d,
            amount_paise=97640,
            account="bank",
            reference=payout.payout_id,
        ),
    ]
    return bank, payout, ledgers


def test_guardrail_accepts_valid() -> None:
    """Valid proposal passing all thresholds is accepted."""
    bank, payout, ledgers = _make_sample_data()
    validator = GuardrailValidator(
        config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        bank_txns=[bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )
    proposal = MatchProposal(
        bank_id=bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[entry.ledger_id for entry in ledgers],
        confidence=0.85,
        fields_matched=["amount_net", "date"],
        reason="Good match",
    )
    verdict = validator.validate(proposal)
    assert verdict.status == "accepted"
    assert len(verdict.reasons) == 0


def test_guardrail_rejects_low_confidence() -> None:
    """Proposal with confidence below threshold is rejected."""
    bank, payout, ledgers = _make_sample_data()
    validator = GuardrailValidator(
        config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        bank_txns=[bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )
    proposal = MatchProposal(
        bank_id=bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[entry.ledger_id for entry in ledgers],
        confidence=0.65,
        fields_matched=["amount_net", "date"],
        reason="Weak match",
    )
    verdict = validator.validate(proposal)
    assert verdict.status == "rejected"
    assert "low_confidence" in verdict.reasons


def test_guardrail_rejects_single_field() -> None:
    """Proposal matching fewer than min_fields is rejected."""
    bank, payout, ledgers = _make_sample_data()
    validator = GuardrailValidator(
        config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        bank_txns=[bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )
    proposal = MatchProposal(
        bank_id=bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[entry.ledger_id for entry in ledgers],
        confidence=0.90,
        fields_matched=["amount_net"],
        reason="Only amount matched",
    )
    verdict = validator.validate(proposal)
    assert verdict.status == "rejected"
    assert "single_field" in verdict.reasons


def test_guardrail_rejects_hallucinated_ids() -> None:
    """Proposal containing non-existent ID is rejected."""
    bank, payout, ledgers = _make_sample_data()
    validator = GuardrailValidator(
        config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        bank_txns=[bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )
    proposal = MatchProposal(
        bank_id="BNK-999999",
        payout_id=payout.payout_id,
        ledger_ids=[entry.ledger_id for entry in ledgers],
        confidence=0.90,
        fields_matched=["amount_net", "date"],
        reason="Hallucinated bank",
    )
    verdict = validator.validate(proposal)
    assert verdict.status == "rejected"
    assert "hallucinated_id" in verdict.reasons


def test_guardrail_rejects_delta_too_large() -> None:
    """Proposal with amount delta exceeding tolerance is rejected."""
    bank, payout, ledgers = _make_sample_data()
    bad_bank = bank.model_copy(update={"amount_paise": bank.amount_paise + 2000})
    validator = GuardrailValidator(
        config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        bank_txns=[bad_bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )
    proposal = MatchProposal(
        bank_id=bad_bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[entry.ledger_id for entry in ledgers],
        confidence=0.90,
        fields_matched=["amount_net", "date"],
        reason="High delta match",
    )
    verdict = validator.validate(proposal)
    assert verdict.status == "rejected"
    assert "delta_too_large" in verdict.reasons


def test_guardrail_rejects_excessive_skew() -> None:
    """Proposal with date skew exceeding tolerance (> 2 days) is rejected."""
    bank, payout, ledgers = _make_sample_data()
    bad_bank = bank.model_copy(update={"value_date": date(2026, 8, 10)})
    validator = GuardrailValidator(
        config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        bank_txns=[bad_bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )
    proposal = MatchProposal(
        bank_id=bad_bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[entry.ledger_id for entry in ledgers],
        confidence=0.90,
        fields_matched=["amount_net", "date"],
        reason="Delayed match",
    )
    verdict = validator.validate(proposal)
    assert verdict.status == "rejected"
    assert "skew_too_large" in verdict.reasons
