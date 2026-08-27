"""Deterministic matching rule stack (checks 2.3-2.7, D1, D2, D23).

Executes the baseline rule stack over the candidate space:
  - Exact UTR & amount matching (clean, drift, timing_tolerated)
  - Duplicate payout detection
  - UTR recovery from narration
  - Refund reversal pair matching
  - Unmatched residual classification into exception buckets
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.core.matching.attribute import attribute_triad_outlier
from engine.core.models import (
    ExceptionBucket,
    GroupKind,
    MatchGroup,
    ReconException,
    ResolvedTag,
    TruthLink,
)

if TYPE_CHECKING:
    from engine.core.models import BankTxn, GatewayPayout, LedgerEntry

PAYOUT_ID_PATTERN = re.compile(r"pout_SYNTH\d{8}")


@dataclass
class MatchResult:
    """Output of the deterministic matching pipeline."""

    matched_groups: list[MatchGroup] = field(default_factory=list)
    exceptions: list[ReconException] = field(default_factory=list)
    predicted_links: list[TruthLink] = field(default_factory=list)


class DeterministicMatcher:
    """Registry-driven deterministic rule matcher (§7 P2)."""

    def __init__(
        self,
        drift_tolerance_paise: int = 50,
        skew_tolerance_days: int = 2,
        enable_dedup: bool = True,
    ) -> None:
        self.drift_tolerance_paise = drift_tolerance_paise
        self.skew_tolerance_days = skew_tolerance_days
        self.enable_dedup = enable_dedup

    def match(
        self,
        bank_txns: list[BankTxn],
        gateway_payouts: list[GatewayPayout],
        ledger_entries: list[LedgerEntry],
    ) -> MatchResult:
        """Run the deterministic reconciliation rules over the inputs."""
        result = MatchResult()

        handled_bank_ids: set[str] = set()
        handled_payout_ids: set[str] = set()
        handled_ledger_ids: set[str] = set()

        payout_by_id = {p.payout_id: p for p in gateway_payouts}

        # Index ledger entries by reference (payout_id)
        ledgers_by_ref: dict[str, list[LedgerEntry]] = {}
        for entry in ledger_entries:
            ledgers_by_ref.setdefault(entry.reference, []).append(entry)

        # Index payouts and banks by non-null UTR
        payouts_by_utr: dict[str, list[GatewayPayout]] = {}
        for p in gateway_payouts:
            if p.utr is not None:
                payouts_by_utr.setdefault(p.utr, []).append(p)

        banks_by_utr: dict[str, list[BankTxn]] = {}
        for b in bank_txns:
            if b.utr is not None:
                banks_by_utr.setdefault(b.utr, []).append(b)

        group_seq = 0
        exception_seq = 0

        # --- Rule 1: UTR Matching ---
        for utr, b_list in banks_by_utr.items():
            if utr not in payouts_by_utr:
                continue

            p_list = payouts_by_utr[utr]

            # Duplicate Payouts on same UTR
            if self.enable_dedup and len(p_list) > 1 and len(b_list) == 1:
                bank = b_list[0]
                row_ids = [bank.bank_id] + [p.payout_id for p in p_list]
                for p in p_list:
                    for l_entry in ledgers_by_ref.get(p.payout_id, []):
                        row_ids.append(l_entry.ledger_id)
                        handled_ledger_ids.add(l_entry.ledger_id)
                    handled_payout_ids.add(p.payout_id)
                handled_bank_ids.add(bank.bank_id)

                exception_seq += 1
                result.exceptions.append(
                    ReconException(
                        exception_id=f"EX-{exception_seq:04d}",
                        row_ids=sorted(row_ids),
                        bucket=ExceptionBucket.DUPLICATE,
                        severity="high",
                        evidence=[
                            f"bank.utr={utr}",
                            f"duplicate payouts count={len(p_list)}",
                        ],
                        proposed_action="Review retried payouts; exactly one is real",
                    )
                )
                continue

            # 1:1 Bank to Payout on UTR
            if len(b_list) == 1 and len(p_list) == 1:
                bank = b_list[0]
                payout = p_list[0]
                ledgers = ledgers_by_ref.get(payout.payout_id, [])

                # Check timing skew
                skew_days = 0
                if payout.settled_at is not None:
                    skew_days = abs((bank.value_date - payout.settled_at.date()).days)

                if skew_days > self.skew_tolerance_days:
                    # Timing break exception
                    exception_seq += 1
                    row_ids = [bank.bank_id, payout.payout_id] + [
                        entry.ledger_id for entry in ledgers
                    ]
                    result.exceptions.append(
                        ReconException(
                            exception_id=f"EX-{exception_seq:04d}",
                            row_ids=sorted(row_ids),
                            bucket=ExceptionBucket.TIMING_BREAK,
                            severity="medium",
                            evidence=[
                                f"bank.date={bank.value_date}",
                                f"payout.date={payout.settled_at.date()}"
                                if payout.settled_at
                                else "payout.date=none",
                                f"skew_days={skew_days} > {self.skew_tolerance_days}d",
                            ],
                            proposed_action="Investigate settlement delay with bank",
                        )
                    )
                else:
                    # Attribute triad outlier
                    verdict, tag, bucket = attribute_triad_outlier(bank, payout, ledgers)

                    if verdict == "resolved" and tag is not None:
                        group_seq += 1
                        # If date skewed within tolerance, use TIMING_TOLERATED tag
                        actual_tag = ResolvedTag.TIMING_TOLERATED if skew_days > 0 else tag
                        result.matched_groups.append(
                            MatchGroup(
                                group_id=f"MG-{group_seq:04d}",
                                kind=GroupKind.SIMPLE,
                                bank_ids=[bank.bank_id],
                                payout_ids=[payout.payout_id],
                                ledger_ids=[entry.ledger_id for entry in ledgers],
                                confidence=1.0,
                                source="deterministic",
                                fields_matched=["utr", "amount_net", "date"],
                                tolerances_used=[f"drift_lte_{self.drift_tolerance_paise}p"],
                                tag=actual_tag,
                                reason="Deterministic 1:1 UTR and amount match",
                                agent_turns=0,
                            )
                        )
                        # Add predicted links
                        result.predicted_links.append(
                            TruthLink(
                                link_type="bank_payout",
                                left_id=bank.bank_id,
                                right_id=payout.payout_id,
                                is_match=True,
                            )
                        )
                        for entry in ledgers:
                            result.predicted_links.append(
                                TruthLink(
                                    link_type="payout_ledger",
                                    left_id=payout.payout_id,
                                    right_id=entry.ledger_id,
                                    is_match=True,
                                )
                            )
                    else:
                        exception_seq += 1
                        row_ids = [bank.bank_id, payout.payout_id] + [
                            entry.ledger_id for entry in ledgers
                        ]
                        act_bucket = bucket or ExceptionBucket.AMOUNT_MISMATCH
                        result.exceptions.append(
                            ReconException(
                                exception_id=f"EX-{exception_seq:04d}",
                                row_ids=sorted(row_ids),
                                bucket=act_bucket,
                                severity="high",
                                evidence=[
                                    f"bank.amount_paise={bank.amount_paise}",
                                    f"payout.net_paise={payout.net_paise}",
                                    f"delta={abs(bank.amount_paise - payout.net_paise)}p",
                                ],
                                proposed_action="Investigate amount/fee disparity with gateway",
                            )
                        )

                handled_bank_ids.add(bank.bank_id)
                handled_payout_ids.add(payout.payout_id)
                for entry in ledgers:
                    handled_ledger_ids.add(entry.ledger_id)

        # --- Rule 2: UTR Recovery from Narration ---
        for bank in bank_txns:
            if bank.bank_id in handled_bank_ids or bank.utr is not None:
                continue

            match = PAYOUT_ID_PATTERN.search(bank.narration)
            if match:
                p_id = match.group(0)
                if p_id in payout_by_id and p_id not in handled_payout_ids:
                    payout = payout_by_id[p_id]
                    ledgers = ledgers_by_ref.get(payout.payout_id, [])

                    group_seq += 1
                    result.matched_groups.append(
                        MatchGroup(
                            group_id=f"MG-{group_seq:04d}",
                            kind=GroupKind.SIMPLE,
                            bank_ids=[bank.bank_id],
                            payout_ids=[payout.payout_id],
                            ledger_ids=[entry.ledger_id for entry in ledgers],
                            confidence=0.95,
                            source="deterministic",
                            fields_matched=["narration_payout_id", "amount_net"],
                            tolerances_used=[],
                            tag=ResolvedTag.UTR_RECOVERED,
                            reason="UTR recovered from bank narration payout reference",
                            agent_turns=0,
                        )
                    )
                    result.predicted_links.append(
                        TruthLink(
                            link_type="bank_payout",
                            left_id=bank.bank_id,
                            right_id=payout.payout_id,
                            is_match=True,
                        )
                    )
                    for entry in ledgers:
                        result.predicted_links.append(
                            TruthLink(
                                link_type="payout_ledger",
                                left_id=payout.payout_id,
                                right_id=entry.ledger_id,
                                is_match=True,
                            )
                        )

                    handled_bank_ids.add(bank.bank_id)
                    handled_payout_ids.add(payout.payout_id)
                    for entry in ledgers:
                        handled_ledger_ids.add(entry.ledger_id)

        # --- Rule 3: Refund Pair Reversal ---
        for payout in gateway_payouts:
            if payout.payout_id in handled_payout_ids or payout.status != "reversed":
                continue

            ledgers = ledgers_by_ref.get(payout.payout_id, [])
            if len(ledgers) == 8 and sum(entry.amount_paise for entry in ledgers) == 0:
                group_seq += 1
                result.matched_groups.append(
                    MatchGroup(
                        group_id=f"MG-{group_seq:04d}",
                        kind=GroupKind.REFUND_PAIR,
                        bank_ids=[],
                        payout_ids=[payout.payout_id],
                        ledger_ids=[entry.ledger_id for entry in ledgers],
                        confidence=1.0,
                        source="deterministic",
                        fields_matched=["payout_id", "balanced_reversal_journals"],
                        tolerances_used=[],
                        tag=ResolvedTag.REFUND,
                        reason="Settlement plus offsetting reversal journal within 7d",
                        agent_turns=0,
                    )
                )
                for entry in ledgers:
                    result.predicted_links.append(
                        TruthLink(
                            link_type="payout_ledger",
                            left_id=payout.payout_id,
                            right_id=entry.ledger_id,
                            is_match=True,
                        )
                    )

                handled_payout_ids.add(payout.payout_id)
                for entry in ledgers:
                    handled_ledger_ids.add(entry.ledger_id)

        # --- Rule 4: Unhandled Residuals -> Exceptions ---
        # 1. Unhandled Payouts
        for payout in gateway_payouts:
            if payout.payout_id in handled_payout_ids:
                continue

            ledgers = ledgers_by_ref.get(payout.payout_id, [])
            for entry in ledgers:
                handled_ledger_ids.add(entry.ledger_id)
            handled_payout_ids.add(payout.payout_id)

            exception_seq += 1
            row_ids = [payout.payout_id] + [entry.ledger_id for entry in ledgers]
            result.exceptions.append(
                ReconException(
                    exception_id=f"EX-{exception_seq:04d}",
                    row_ids=sorted(row_ids),
                    bucket=ExceptionBucket.MISSING_UTR,
                    severity="high",
                    evidence=[
                        f"payout.amount_paise={payout.amount_paise}",
                        "payout.utr=None",
                    ],
                    proposed_action="Obtain UTR from bank statement",
                )
            )

        # 2. Unhandled Banks
        for bank in bank_txns:
            if bank.bank_id in handled_bank_ids:
                continue

            handled_bank_ids.add(bank.bank_id)
            exception_seq += 1
            bucket = (
                ExceptionBucket.MISSING_UTR if bank.utr is None else ExceptionBucket.ORPHAN_BANK
            )
            result.exceptions.append(
                ReconException(
                    exception_id=f"EX-{exception_seq:04d}",
                    row_ids=[bank.bank_id],
                    bucket=bucket,
                    severity="high" if bucket == ExceptionBucket.MISSING_UTR else "medium",
                    evidence=[
                        f"bank.amount_paise={bank.amount_paise}",
                        f"bank.utr={bank.utr}",
                        f"bank.narration={bank.narration}",
                    ],
                    proposed_action="Trace credit with bank; no matching payout found",
                )
            )

        # 3. Unhandled Ledgers (grouped by journal_id)
        journals_unhandled: dict[str, list[LedgerEntry]] = {}
        for entry in ledger_entries:
            if entry.ledger_id not in handled_ledger_ids:
                journals_unhandled.setdefault(entry.journal_id, []).append(entry)

        for _, j_entries in journals_unhandled.items():
            for entry in j_entries:
                handled_ledger_ids.add(entry.ledger_id)

            exception_seq += 1
            has_positive_rec = any(
                e.account == "settlements_receivable" and e.amount_paise > 0 for e in j_entries
            )
            bucket = (
                ExceptionBucket.REFUND_UNPAIRED
                if has_positive_rec
                else ExceptionBucket.ORPHAN_LEDGER
            )

            result.exceptions.append(
                ReconException(
                    exception_id=f"EX-{exception_seq:04d}",
                    row_ids=sorted(e.ledger_id for e in j_entries),
                    bucket=bucket,
                    severity="medium",
                    evidence=[
                        f"journal.id={j_entries[0].journal_id}",
                        f"journal.lines={len(j_entries)}",
                    ],
                    proposed_action="Investigate unpaired journal in general ledger",
                )
            )

        return result


class InvertedMatcher:
    """Adversarial matcher with inverted amount/UTR matching logic (§4.6, check 5.14)."""

    def __init__(
        self,
        drift_tolerance_paise: int = 50,
        skew_tolerance_days: int = 2,
    ) -> None:
        self.drift_tolerance_paise = drift_tolerance_paise
        self.skew_tolerance_days = skew_tolerance_days

    def match(
        self,
        bank_txns: list[BankTxn],
        gateway_payouts: list[GatewayPayout],
        ledger_entries: list[LedgerEntry],
    ) -> MatchResult:
        """Pair transactions where amounts and UTRs are completely mismatched."""
        result = MatchResult()
        payouts_reversed = list(reversed(gateway_payouts))

        for idx, bank in enumerate(bank_txns):
            if idx < len(payouts_reversed):
                payout = payouts_reversed[idx]
                if bank.utr != payout.utr and abs(bank.amount_paise - payout.net_paise) > 100:
                    result.matched_groups.append(
                        MatchGroup(
                            group_id=f"MG-INV-{idx:04d}",
                            kind=GroupKind.SIMPLE,
                            bank_ids=[bank.bank_id],
                            payout_ids=[payout.payout_id],
                            ledger_ids=[],
                            confidence=0.10,
                            source="deterministic",
                            fields_matched=[],
                            tolerances_used=[],
                            tag=ResolvedTag.CLEAN,
                            reason="Inverted adversarial pairing",
                            agent_turns=0,
                        )
                    )
        return result
