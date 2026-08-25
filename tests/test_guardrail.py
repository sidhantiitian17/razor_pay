"""Tests for guardrail validation and safety filters (check 3.7, §3.6, R8, D15)."""

from datetime import UTC, date, datetime

from engine.core.guardrail import (
    GuardrailConfig,
    GuardrailValidator,
    GuardrailVerdict,
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


def test_guardrail_config_defaults_and_immutability() -> None:
    """Config has exact default values, to_dict serialization, and is frozen."""
    import dataclasses

    cfg = GuardrailConfig()
    assert cfg.min_confidence == 0.70
    assert cfg.min_fields == 2
    assert cfg.max_drift_paise == 50
    assert cfg.max_skew_days == 2
    assert cfg.max_pct_delta == 0.01

    d = cfg.to_dict()
    assert d == {
        "min_confidence": 0.70,
        "min_fields": 2,
        "max_drift_paise": 50,
        "max_skew_days": 2,
        "max_pct_delta": 0.01,
    }

    try:
        cfg.min_confidence = 0.90  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("GuardrailConfig must be frozen")


def test_guardrail_dataclasses_frozen() -> None:
    """MatchProposal and GuardrailVerdict are frozen dataclasses."""
    import dataclasses

    prop = MatchProposal(
        bank_id="B1",
        payout_id="P1",
        ledger_ids=["L1"],
        confidence=0.8,
        fields_matched=["a", "b"],
        reason="test",
    )
    try:
        prop.confidence = 0.5  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("MatchProposal must be frozen")

    v = GuardrailVerdict(status="accepted")
    assert v.reasons == []
    try:
        v.status = "rejected"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("GuardrailVerdict must be frozen")


def test_guardrail_boundary_confidence_and_fields() -> None:
    """Exact boundary conditions for confidence and fields_matched."""
    bank, payout, ledgers = _make_sample_data()
    validator = GuardrailValidator(
        config=GuardrailConfig(),
        bank_txns=[bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )

    # Exact threshold 0.70 passes
    prop_exact = MatchProposal(
        bank_id=bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[e.ledger_id for e in ledgers],
        confidence=0.70,
        fields_matched=["f1", "f2"],
        reason="exact threshold",
    )
    assert validator.validate(prop_exact).status == "accepted"

    # 0.6999 fails
    prop_low = MatchProposal(
        bank_id=bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[e.ledger_id for e in ledgers],
        confidence=0.6999,
        fields_matched=["f1", "f2"],
        reason="below threshold",
    )
    v = validator.validate(prop_low)
    assert v.status == "rejected"
    assert "low_confidence" in v.reasons

    # Exactly 2 fields passes
    prop_2 = MatchProposal(
        bank_id=bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[e.ledger_id for e in ledgers],
        confidence=0.85,
        fields_matched=["f1", "f2"],
        reason="2 fields",
    )
    assert validator.validate(prop_2).status == "accepted"

    # 1 field fails
    prop_1 = MatchProposal(
        bank_id=bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[e.ledger_id for e in ledgers],
        confidence=0.85,
        fields_matched=["f1"],
        reason="1 field",
    )
    v_1 = validator.validate(prop_1)
    assert v_1.status == "rejected"
    assert "single_field" in v_1.reasons


def test_guardrail_hallucination_individual_branches() -> None:
    """Missing bank, payout, or ledger ID individually trigger hallucinated_id."""
    bank, payout, ledgers = _make_sample_data()
    validator = GuardrailValidator(
        config=GuardrailConfig(),
        bank_txns=[bank],
        gateway_payouts=[payout],
        ledger_entries=ledgers,
    )

    # Missing bank
    v_bank = validator.validate(
        MatchProposal(
            bank_id="MISSING",
            payout_id=payout.payout_id,
            ledger_ids=[e.ledger_id for e in ledgers],
            confidence=0.85,
            fields_matched=["f1", "f2"],
            reason="test",
        )
    )
    assert v_bank.status == "rejected"
    assert "hallucinated_id" in v_bank.reasons

    # Missing payout
    v_payout = validator.validate(
        MatchProposal(
            bank_id=bank.bank_id,
            payout_id="MISSING",
            ledger_ids=[e.ledger_id for e in ledgers],
            confidence=0.85,
            fields_matched=["f1", "f2"],
            reason="test",
        )
    )
    assert v_payout.status == "rejected"
    assert "hallucinated_id" in v_payout.reasons

    # Missing ledger
    v_ledger = validator.validate(
        MatchProposal(
            bank_id=bank.bank_id,
            payout_id=payout.payout_id,
            ledger_ids=[ledgers[0].ledger_id, "MISSING_LEDGER"],
            confidence=0.85,
            fields_matched=["f1", "f2"],
            reason="test",
        )
    )
    assert v_ledger.status == "rejected"
    assert "hallucinated_id" in v_ledger.reasons


def test_guardrail_delta_and_skew_tolerances() -> None:
    """Drift tolerance boundaries and percentage tolerance logic."""
    bank, payout, ledgers = _make_sample_data()

    # Case 1: drift == 50 paise (<= max_drift_paise=50) -> passes
    bank_50 = bank.model_copy(update={"amount_paise": payout.net_paise + 50})
    v50 = GuardrailValidator(
        GuardrailConfig(max_drift_paise=50, max_pct_delta=0.001),
        [bank_50],
        [payout],
        ledgers,
    ).validate(
        MatchProposal(
            bank_id=bank_50.bank_id,
            payout_id=payout.payout_id,
            ledger_ids=[e.ledger_id for e in ledgers],
            confidence=0.9,
            fields_matched=["a", "b"],
            reason="test",
        )
    )
    assert v50.status == "accepted"

    # Case 2: drift == 51 paise and drift > pct_tol
    # (payout 100000 paise * 0.0001 = 10 paise) -> fails
    bank_51 = bank.model_copy(update={"amount_paise": payout.net_paise + 51})
    v51 = GuardrailValidator(
        GuardrailConfig(max_drift_paise=50, max_pct_delta=0.0001),
        [bank_51],
        [payout],
        ledgers,
    ).validate(
        MatchProposal(
            bank_id=bank_51.bank_id,
            payout_id=payout.payout_id,
            ledger_ids=[e.ledger_id for e in ledgers],
            confidence=0.9,
            fields_matched=["a", "b"],
            reason="test",
        )
    )
    assert v51.status == "rejected"
    assert "delta_too_large" in v51.reasons

    # Case 3: drift = 100 paise (> max_drift_paise=50), but pct_tol is 500 paise
    # (payout 5000000 * 0.01 = 50000) -> passes
    big_payout = payout.model_copy(update={"amount_paise": 5000000, "fee_paise": 0, "tax_paise": 0})
    bank_100 = bank.model_copy(update={"amount_paise": 5000100})
    v100 = GuardrailValidator(
        GuardrailConfig(max_drift_paise=50, max_pct_delta=0.01),
        [bank_100],
        [big_payout],
        ledgers,
    ).validate(
        MatchProposal(
            bank_id=bank_100.bank_id,
            payout_id=big_payout.payout_id,
            ledger_ids=[e.ledger_id for e in ledgers],
            confidence=0.9,
            fields_matched=["a", "b"],
            reason="test",
        )
    )
    assert v100.status == "accepted"

    # Case 4: skew == 2 days (<= max_skew_days=2) -> passes
    bank_skew2 = bank.model_copy(update={"value_date": date(2026, 8, 3)})
    v_skew2 = GuardrailValidator(
        GuardrailConfig(max_skew_days=2),
        [bank_skew2],
        [payout],
        ledgers,
    ).validate(
        MatchProposal(
            bank_id=bank_skew2.bank_id,
            payout_id=payout.payout_id,
            ledger_ids=[e.ledger_id for e in ledgers],
            confidence=0.9,
            fields_matched=["a", "b"],
            reason="test",
        )
    )
    assert v_skew2.status == "accepted"

    # Case 5: payout.settled_at is None -> passes without skew check
    payout_no_settled = payout.model_copy(update={"settled_at": None})
    v_no_settled = GuardrailValidator(
        GuardrailConfig(max_skew_days=2),
        [bank_skew2],
        [payout_no_settled],
        ledgers,
    ).validate(
        MatchProposal(
            bank_id=bank_skew2.bank_id,
            payout_id=payout_no_settled.payout_id,
            ledger_ids=[e.ledger_id for e in ledgers],
            confidence=0.9,
            fields_matched=["a", "b"],
            reason="test",
        )
    )
    assert v_no_settled.status == "accepted"


def test_guardrail_multiple_reasons_rejection() -> None:
    """Multiple reasons are accumulated when multiple rules fail."""
    bank, payout, ledgers = _make_sample_data()
    bad_bank = bank.model_copy(
        update={"amount_paise": bank.amount_paise + 5000, "value_date": date(2026, 8, 20)}
    )
    validator = GuardrailValidator(
        GuardrailConfig(),
        [bad_bank],
        [payout],
        ledgers,
    )
    proposal = MatchProposal(
        bank_id=bad_bank.bank_id,
        payout_id=payout.payout_id,
        ledger_ids=[e.ledger_id for e in ledgers],
        confidence=0.50,
        fields_matched=["only_one"],
        reason="Multiple failures",
    )
    v = validator.validate(proposal)
    assert v.status == "rejected"
    assert set(v.reasons) == {"low_confidence", "single_field", "delta_too_large", "skew_too_large"}
