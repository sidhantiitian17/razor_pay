"""Cohort injectors and terminal state definitions (§3.5, I6, I7, D1, D2, D3).

Every cohort maps to exactly one terminal state, and all 13 injectors
are registered in COHORT_INJECTORS and COHORT_TERMINAL_MAP.
"""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from random import Random  # noqa: TC003

from engine.core.generator.journals import (
    make_refund_reversal_journal,
    make_settlement_journal,
)
from engine.core.models import (
    BankTxn,
    CohortName,
    ExceptionBucket,
    GatewayPayout,
    GroupKind,
    LedgerEntry,
    ResolvedTag,
    TruthGroup,
)

# Base date for deterministic generation: 2026-08-01 UTC
BASE_DATETIME = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
BASE_DATE = date(2026, 8, 1)

COHORT_TERMINAL_MAP: dict[CohortName, tuple[str, ResolvedTag | None, ExceptionBucket | None]] = {
    CohortName.CLEAN: ("resolved", ResolvedTag.CLEAN, None),
    CohortName.DRIFT_TOLERATED: ("resolved", ResolvedTag.DRIFT, None),
    CohortName.DRIFT_EXCEPTION: ("unresolved", None, ExceptionBucket.AMOUNT_MISMATCH),
    CohortName.SKEW_TOLERATED: ("resolved", ResolvedTag.TIMING_TOLERATED, None),
    CohortName.SKEW_EXCEPTION: ("unresolved", None, ExceptionBucket.TIMING_BREAK),
    CohortName.MISSING_UTR_RECOVERABLE: ("resolved", ResolvedTag.UTR_RECOVERED, None),
    CohortName.MISSING_UTR_UNRECOVERABLE: ("unresolved", None, ExceptionBucket.MISSING_UTR),
    CohortName.DUPLICATE_PAYOUT: ("unresolved", None, ExceptionBucket.DUPLICATE),
    CohortName.REFUND_PAIR: ("resolved", ResolvedTag.REFUND, None),
    CohortName.REFUND_UNPAIRED: ("unresolved", None, ExceptionBucket.REFUND_UNPAIRED),
    CohortName.FEE_MISMATCH: ("unresolved", None, ExceptionBucket.FEE_MISMATCH),
    CohortName.ORPHAN_BANK: ("unresolved", None, ExceptionBucket.ORPHAN_BANK),
    CohortName.ORPHAN_LEDGER: ("unresolved", None, ExceptionBucket.ORPHAN_LEDGER),
}


@dataclass(frozen=True)
class InjectedCohort:
    """Output bundle of one cohort injection."""

    truth_group: TruthGroup
    bank_txns: list[BankTxn]
    gateway_payouts: list[GatewayPayout]
    ledger_entries: list[LedgerEntry]


@dataclass
class IdCounters:
    """Sequential ID generators for all entity types."""

    bank: int = 0
    payout: int = 0
    ledger: int = 0
    journal: int = 0
    group: int = 0
    utr: int = 0

    def next_bank_id(self) -> str:
        """Generate next sequential Bank transaction ID."""
        self.bank += 1
        return f"BNK-{self.bank:06d}"

    def next_payout_id(self) -> str:
        """Generate next sequential Gateway payout ID."""
        self.payout += 1
        return f"pout_SYNTH{self.payout:08d}"

    def next_ledger_id(self) -> str:
        """Generate next sequential Ledger entry ID."""
        self.ledger += 1
        return f"LED-{self.ledger:06d}"

    def next_journal_id(self) -> str:
        """Generate next sequential Journal ID."""
        self.journal += 1
        return f"JRN-{self.journal:06d}"

    def next_group_id(self) -> str:
        """Generate next sequential Truth group ID."""
        self.group += 1
        return f"TG-{self.group:04d}"

    def next_utr(self) -> str:
        """Generate next sequential synthetic UTR."""
        self.utr += 1
        return f"SYNTH{self.utr:017d}"


def _make_base_settlement(
    counters: IdCounters,
    rng: Random,
    offset_days: int = 0,
) -> tuple[str, str, int, int, int, int, datetime, date]:
    """Generate base parameters for a settlement."""
    payout_id = counters.next_payout_id()
    utr = counters.next_utr()

    # Gross amount between 500.00 and 50,000.00 INR (50,000 to 5,000,000 paise)
    gross_paise = rng.randint(50000, 5000000)
    # Fee is 2% of gross + base fee
    fee_paise = int(gross_paise * 0.02) + rng.randint(100, 500)
    # Tax is 18% of fee
    tax_paise = int(fee_paise * 0.18)
    net_paise = gross_paise - fee_paise - tax_paise

    settled_at = BASE_DATETIME + timedelta(days=offset_days, minutes=rng.randint(0, 480))
    value_date = BASE_DATE + timedelta(days=offset_days)

    return (
        payout_id,
        utr,
        gross_paise,
        fee_paise,
        tax_paise,
        net_paise,
        settled_at,
        value_date,
    )


def inject_clean(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject clean 1:1:4 settlement with identical UTR, exact amount, and aligned date."""
    payout_id, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=settled_at,
        value_date=value_date,
        amount_paise=net,
        utr=utr,
        narration=f"CMS/SYNTH/{utr}/SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.CLEAN,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="resolved",
        expected_tag=ResolvedTag.CLEAN,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_drift_tolerated(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement with acceptable drift in bank amount (1-49 paise)."""
    payout_id, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    drift = rng.choice([-1, 1]) * rng.randint(1, 49)
    bank_amount = net + drift

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=settled_at,
        value_date=value_date,
        amount_paise=bank_amount,
        utr=utr,
        narration=f"CMS/SYNTH/{utr}/SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.DRIFT_TOLERATED,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="resolved",
        expected_tag=ResolvedTag.DRIFT,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_drift_exception(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement with excessive drift (80-200 paise) resulting in amount_mismatch."""
    payout_id, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    drift = rng.choice([-1, 1]) * rng.randint(80, 200)
    bank_amount = net + drift

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=settled_at,
        value_date=value_date,
        amount_paise=bank_amount,
        utr=utr,
        narration=f"CMS/SYNTH/{utr}/SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.DRIFT_EXCEPTION,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.AMOUNT_MISMATCH,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_skew_tolerated(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement with acceptable timing skew (1-2 days)."""
    payout_id, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    skew_days = rng.choice([-1, 1]) * rng.randint(1, 2)
    bank_value_date = value_date + timedelta(days=skew_days)
    bank_posted_at = settled_at + timedelta(days=skew_days)

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=bank_posted_at,
        value_date=bank_value_date,
        amount_paise=net,
        utr=utr,
        narration=f"CMS/SYNTH/{utr}/SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.SKEW_TOLERATED,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="resolved",
        expected_tag=ResolvedTag.TIMING_TOLERATED,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_skew_exception(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement with timing break exceeding tolerance (3-5 days)."""
    payout_id, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    skew_days = rng.choice([-1, 1]) * rng.randint(3, 5)
    bank_value_date = value_date + timedelta(days=skew_days)
    bank_posted_at = settled_at + timedelta(days=skew_days)

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=bank_posted_at,
        value_date=bank_value_date,
        amount_paise=net,
        utr=utr,
        narration=f"CMS/SYNTH/{utr}/SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.SKEW_EXCEPTION,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.TIMING_BREAK,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_missing_utr_recoverable(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement with missing UTR on bank side, but recoverable from narration."""
    payout_id, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    # UTR nulled on bank side, but payout_id is present in narration
    bank = BankTxn(
        bank_id=bank_id,
        posted_at=settled_at,
        value_date=value_date,
        amount_paise=net,
        utr=None,
        narration=f"SETTLEMENT/{payout_id}/RZP",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.MISSING_UTR_RECOVERABLE,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="resolved",
        expected_tag=ResolvedTag.UTR_RECOVERED,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_missing_utr_unrecoverable(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement with missing UTRs and scrubbed narration (unrecoverable)."""
    payout_id, _, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    # Both UTRs None and narration scrubbed
    bank = BankTxn(
        bank_id=bank_id,
        posted_at=settled_at,
        value_date=value_date,
        amount_paise=net,
        utr=None,
        narration="DIRECT CREDIT SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=None,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.MISSING_UTR_UNRECOVERABLE,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.MISSING_UTR,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_duplicate_payout(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject retried payout resulting in duplicate settlement instruction."""
    payout_id1, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    payout_id2 = counters.next_payout_id()
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=settled_at,
        value_date=value_date,
        amount_paise=net,
        utr=utr,
        narration=f"CMS/SYNTH/{utr}/SETTLEMENT",
    )
    payout1 = GatewayPayout(
        payout_id=payout_id1,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    # Duplicate payout: same UTR and amount, retried
    payout2 = GatewayPayout(
        payout_id=payout_id2,
        created_at=settled_at - timedelta(hours=1),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id1,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.DUPLICATE_SET,
        cohort=CohortName.DUPLICATE_PAYOUT,
        bank_ids=[bank_id],
        payout_ids=[payout_id1, payout_id2],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.DUPLICATE,
    )
    return InjectedCohort(tg, [bank], [payout1, payout2], ledgers)


def inject_refund_pair(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement plus offsetting reversal journal within 7 days."""
    payout_id, utr, gross, fee, tax, _, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    journal_id1 = counters.next_journal_id()
    journal_id2 = counters.next_journal_id()

    # Settlement journal
    ledgers1 = make_settlement_journal(
        journal_id=journal_id1,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    # Offsetting reversal journal within 7 days
    reversal_date = value_date + timedelta(days=rng.randint(1, 5))
    ledgers2 = make_refund_reversal_journal(
        journal_id=journal_id2,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=reversal_date,
        id_generator=counters.next_ledger_id,
    )

    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        utr=utr,
        status="reversed",
    )

    all_ledgers = ledgers1 + ledgers2
    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.REFUND_PAIR,
        cohort=CohortName.REFUND_PAIR,
        bank_ids=[],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in all_ledgers],
        expected_outcome="resolved",
        expected_tag=ResolvedTag.REFUND,
    )
    return InjectedCohort(tg, [], [payout], all_ledgers)


def inject_refund_unpaired(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject reversal journal with absent original settlement."""
    payout_id = counters.next_payout_id()
    group_id = counters.next_group_id()
    journal_id = counters.next_journal_id()

    gross = rng.randint(50000, 2000000)
    fee = int(gross * 0.02)
    tax = int(fee * 0.18)
    reversal_date = BASE_DATE + timedelta(days=idx % 30)

    ledgers = make_refund_reversal_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=reversal_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.ORPHAN_LEDGER,
        cohort=CohortName.REFUND_UNPAIRED,
        bank_ids=[],
        payout_ids=[],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.REFUND_UNPAIRED,
    )
    return InjectedCohort(tg, [], [], ledgers)


def inject_fee_mismatch(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject settlement where payout fee is altered, making payout the outlier."""
    payout_id, utr, gross, fee, tax, net, settled_at, value_date = _make_base_settlement(
        counters, rng, offset_days=idx % 30
    )
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()
    journal_id = counters.next_journal_id()

    # Payout has corrupted fee/tax, but ledger and bank reflect expected fee
    perturbed_fee = fee + rng.randint(200, 1000)
    perturbed_tax = int(perturbed_fee * 0.18)

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=settled_at,
        value_date=value_date,
        amount_paise=net,
        utr=utr,
        narration=f"CMS/SYNTH/{utr}/SETTLEMENT",
    )
    payout = GatewayPayout(
        payout_id=payout_id,
        created_at=settled_at - timedelta(hours=2),
        settled_at=settled_at,
        amount_paise=gross,
        fee_paise=perturbed_fee,
        tax_paise=perturbed_tax,
        utr=utr,
        status="processed",
    )
    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=value_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.SIMPLE,
        cohort=CohortName.FEE_MISMATCH,
        bank_ids=[bank_id],
        payout_ids=[payout_id],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.FEE_MISMATCH,
    )
    return InjectedCohort(tg, [bank], [payout], ledgers)


def inject_orphan_bank(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject unrecognised bank credit with no counterpart payout or journal."""
    utr = counters.next_utr()
    group_id = counters.next_group_id()
    bank_id = counters.next_bank_id()

    amount_paise = rng.randint(50000, 2000000)
    value_date = BASE_DATE + timedelta(days=idx % 30)
    posted_at = BASE_DATETIME + timedelta(days=idx % 30)

    bank = BankTxn(
        bank_id=bank_id,
        posted_at=posted_at,
        value_date=value_date,
        amount_paise=amount_paise,
        utr=utr,
        narration=f"NEFT/CREDIT/{utr}/UNRECOGNISED",
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.ORPHAN_BANK,
        cohort=CohortName.ORPHAN_BANK,
        bank_ids=[bank_id],
        payout_ids=[],
        ledger_ids=[],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.ORPHAN_BANK,
    )
    return InjectedCohort(tg, [bank], [], [])


def inject_orphan_ledger(counters: IdCounters, rng: Random, idx: int) -> InjectedCohort:
    """Inject orphan balanced journal with no counterpart bank credit or payout."""
    payout_id = counters.next_payout_id()
    group_id = counters.next_group_id()
    journal_id = counters.next_journal_id()

    gross = rng.randint(50000, 2000000)
    fee = int(gross * 0.02)
    tax = int(fee * 0.18)
    entry_date = BASE_DATE + timedelta(days=idx % 30)

    ledgers = make_settlement_journal(
        journal_id=journal_id,
        payout_id=payout_id,
        gross_paise=gross,
        fee_paise=fee,
        tax_paise=tax,
        entry_date=entry_date,
        id_generator=counters.next_ledger_id,
    )

    tg = TruthGroup(
        group_id=group_id,
        kind=GroupKind.ORPHAN_LEDGER,
        cohort=CohortName.ORPHAN_LEDGER,
        bank_ids=[],
        payout_ids=[],
        ledger_ids=[e.ledger_id for e in ledgers],
        expected_outcome="unresolved",
        expected_bucket=ExceptionBucket.ORPHAN_LEDGER,
    )
    return InjectedCohort(tg, [], [], ledgers)


COHORT_INJECTORS: dict[CohortName, Callable[[IdCounters, Random, int], InjectedCohort]] = {
    CohortName.CLEAN: inject_clean,
    CohortName.DRIFT_TOLERATED: inject_drift_tolerated,
    CohortName.DRIFT_EXCEPTION: inject_drift_exception,
    CohortName.SKEW_TOLERATED: inject_skew_tolerated,
    CohortName.SKEW_EXCEPTION: inject_skew_exception,
    CohortName.MISSING_UTR_RECOVERABLE: inject_missing_utr_recoverable,
    CohortName.MISSING_UTR_UNRECOVERABLE: inject_missing_utr_unrecoverable,
    CohortName.DUPLICATE_PAYOUT: inject_duplicate_payout,
    CohortName.REFUND_PAIR: inject_refund_pair,
    CohortName.REFUND_UNPAIRED: inject_refund_unpaired,
    CohortName.FEE_MISMATCH: inject_fee_mismatch,
    CohortName.ORPHAN_BANK: inject_orphan_bank,
    CohortName.ORPHAN_LEDGER: inject_orphan_ledger,
}
