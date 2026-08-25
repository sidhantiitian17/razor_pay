"""Exception classification and evidence extraction (§3.4, §3.6, R6, D1, I13, check 4.1-4.5).

Pure deterministic classifier mapping unresolved residuals to the 9 exception buckets
with structured, audit-grade evidence strings and proposed remediation actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.core.matching.attribute import attribute_triad_outlier
from engine.core.models import (
    ExceptionBucket,
    GroupKind,
    ReconException,
)

if TYPE_CHECKING:
    from engine.core.models import (
        BankTxn,
        GatewayPayout,
        LedgerEntry,
        MatchGroup,
    )


class ExceptionClassifier:
    """Deterministic classifier for unmatched residual reconciliation exceptions."""

    def classify(
        self,
        bank_txns: list[BankTxn],
        gateway_payouts: list[GatewayPayout],
        ledger_entries: list[LedgerEntry],
        matched_groups: list[MatchGroup],
    ) -> list[ReconException]:
        """Classify all unmatched residuals into the 9 unresolved buckets."""
        matched_bank_ids = {bid for mg in matched_groups for bid in mg.bank_ids}
        matched_payout_ids = {pid for mg in matched_groups for pid in mg.payout_ids}
        matched_ledger_ids = {lid for mg in matched_groups for lid in mg.ledger_ids}

        raw_exceptions: list[ReconException] = []

        # 0. Partial Groups (pipeline error / incomplete match groups)
        for mg in matched_groups:
            is_partial = False
            reasons = []
            if mg.kind == GroupKind.SIMPLE:
                if len(mg.bank_ids) != 1 or len(mg.payout_ids) != 1:
                    is_partial = True
                    b_count = len(mg.bank_ids)
                    p_count = len(mg.payout_ids)
                    reasons.append(f"simple cardinality mismatch: b={b_count}, p={p_count}")
            elif mg.kind == GroupKind.DUPLICATE_SET:
                if len(mg.bank_ids) != 1 or len(mg.payout_ids) != 2:
                    is_partial = True
                    b_count = len(mg.bank_ids)
                    p_count = len(mg.payout_ids)
                    reasons.append(f"duplicate_set cardinality mismatch: b={b_count}, p={p_count}")
            elif mg.kind == GroupKind.REFUND_PAIR and (
                len(mg.payout_ids) != 1 or len(mg.ledger_ids) < 4
            ):
                is_partial = True
                p_count = len(mg.payout_ids)
                l_count = len(mg.ledger_ids)
                reasons.append(f"refund_pair cardinality mismatch: p={p_count}, l={l_count}")

            if is_partial:
                row_ids = mg.bank_ids + mg.payout_ids + mg.ledger_ids
                evidence = [
                    f"group_id={mg.group_id}",
                    f"kind={mg.kind.value}",
                    f"confidence={mg.confidence:.2f}",
                    *reasons,
                ]
                raw_exceptions.append(
                    ReconException(
                        exception_id="temp",
                        row_ids=sorted(row_ids),
                        bucket=ExceptionBucket.PARTIAL_GROUP,
                        severity="medium",
                        evidence=evidence,
                        proposed_action="Review partial match grouping for split counterparts",
                    )
                )

        # Build lookups
        unmatched_banks = [b for b in bank_txns if b.bank_id not in matched_bank_ids]
        unmatched_payouts = [p for p in gateway_payouts if p.payout_id not in matched_payout_ids]
        unmatched_ledgers = [
            entry for entry in ledger_entries if entry.ledger_id not in matched_ledger_ids
        ]

        # Group ledgers by reference / payout_id
        ledgers_by_ref: dict[str, list[LedgerEntry]] = {}
        for entry in ledger_entries:
            ledgers_by_ref.setdefault(entry.reference, []).append(entry)

        # Group ledgers by journal_id
        unmatched_ledgers_by_jrn: dict[str, list[LedgerEntry]] = {}
        for entry in unmatched_ledgers:
            unmatched_ledgers_by_jrn.setdefault(entry.journal_id, []).append(entry)

        # Detect duplicates among payouts
        payouts_by_utr_amt: dict[tuple[str | None, int], list[GatewayPayout]] = {}
        for p in gateway_payouts:
            payouts_by_utr_amt.setdefault((p.utr, p.amount_paise), []).append(p)

        duplicate_payout_ids = {
            p.payout_id for plist in payouts_by_utr_amt.values() if len(plist) > 1 for p in plist
        }

        # Track processed items
        processed_banks: set[str] = set()
        processed_payouts: set[str] = set()
        processed_journals: set[str] = set()

        # 1. Classify Duplicates
        for p in unmatched_payouts:
            if p.payout_id in duplicate_payout_ids and p.payout_id not in processed_payouts:
                same_payouts = payouts_by_utr_amt[(p.utr, p.amount_paise)]
                p_ids = [
                    sp.payout_id for sp in same_payouts if sp.payout_id not in matched_payout_ids
                ]
                for pid in p_ids:
                    processed_payouts.add(pid)
                # Find any associated bank
                related_banks = [b for b in unmatched_banks if b.utr == p.utr and b.utr is not None]
                bank_ids = [b.bank_id for b in related_banks]
                for bid in bank_ids:
                    processed_banks.add(bid)

                evidence = [
                    f"duplicate_payout_count={len(same_payouts)}",
                    f"utr={p.utr}",
                    f"amount_paise={p.amount_paise}",
                    f"net_paise={p.net_paise}",
                ]
                raw_exceptions.append(
                    ReconException(
                        exception_id="temp",
                        row_ids=sorted(bank_ids + p_ids),
                        bucket=ExceptionBucket.DUPLICATE,
                        severity="high",
                        evidence=evidence,
                        proposed_action="Investigate gateway retry or duplicate payout submission",
                    )
                )

        # 2. Classify Unmatched Payouts with matching banks
        for p in unmatched_payouts:
            if p.payout_id in processed_payouts:
                continue

            matching_banks = [
                b
                for b in unmatched_banks
                if b.bank_id not in processed_banks
                and ((b.utr is not None and b.utr == p.utr) or (p.payout_id in b.narration))
            ]

            if matching_banks:
                b = matching_banks[0]
                processed_banks.add(b.bank_id)
                processed_payouts.add(p.payout_id)
                drift = abs(b.amount_paise - p.net_paise)
                skew_days = abs((b.value_date - p.settled_at.date()).days) if p.settled_at else 0

                if skew_days > 2:
                    p_date_str = str(p.settled_at.date() if p.settled_at else None)
                    raw_exceptions.append(
                        ReconException(
                            exception_id="temp",
                            row_ids=sorted([b.bank_id, p.payout_id]),
                            bucket=ExceptionBucket.TIMING_BREAK,
                            severity="medium",
                            evidence=[
                                f"bank.value_date={b.value_date}",
                                f"payout.settled_at={p_date_str}",
                                f"skew_days={skew_days}",
                                f"bank.amount_paise={b.amount_paise}",
                            ],
                            proposed_action="Confirm value date settlement lag (>2d)",
                        )
                    )
                else:
                    # Use 3-way outlier attribution (§3.4)
                    rel_ledgers = ledgers_by_ref.get(p.payout_id, [])
                    _v, _tag, bucket = attribute_triad_outlier(b, p, rel_ledgers)
                    bucket_val = bucket or ExceptionBucket.AMOUNT_MISMATCH

                    if bucket_val == ExceptionBucket.FEE_MISMATCH:
                        raw_exceptions.append(
                            ReconException(
                                exception_id="temp",
                                row_ids=sorted([b.bank_id, p.payout_id]),
                                bucket=ExceptionBucket.FEE_MISMATCH,
                                severity="medium",
                                evidence=[
                                    f"payout.fee_paise={p.fee_paise}",
                                    f"payout.tax_paise={p.tax_paise}",
                                    f"bank.amount_paise={b.amount_paise}",
                                    f"payout.net_paise={p.net_paise}",
                                ],
                                proposed_action="Review gateway fee contract and tax schedule",
                            )
                        )
                    else:
                        raw_exceptions.append(
                            ReconException(
                                exception_id="temp",
                                row_ids=sorted([b.bank_id, p.payout_id]),
                                bucket=ExceptionBucket.AMOUNT_MISMATCH,
                                severity="high",
                                evidence=[
                                    f"bank.amount_paise={b.amount_paise}",
                                    f"payout.net_paise={p.net_paise}",
                                    f"delta_paise={drift}",
                                    f"bank.utr={b.utr}",
                                ],
                                proposed_action="Investigate bank settlement amount discrepancy",
                            )
                        )
            else:
                # No matching bank found for payout
                processed_payouts.add(p.payout_id)
                if p.utr is None:
                    raw_exceptions.append(
                        ReconException(
                            exception_id="temp",
                            row_ids=[p.payout_id],
                            bucket=ExceptionBucket.MISSING_UTR,
                            severity="medium",
                            evidence=[
                                f"payout.payout_id={p.payout_id}",
                                "payout.utr=None",
                                f"payout.amount_paise={p.amount_paise}",
                                f"payout.status={p.status}",
                            ],
                            proposed_action="Request UTR assignment from banking partner",
                        )
                    )
                else:
                    related_ledgers = [e for e in unmatched_ledgers if e.reference == p.payout_id]
                    raw_exceptions.append(
                        ReconException(
                            exception_id="temp",
                            row_ids=sorted([p.payout_id] + [e.ledger_id for e in related_ledgers]),
                            bucket=ExceptionBucket.ORPHAN_BANK,
                            severity="low",
                            evidence=[
                                f"payout.payout_id={p.payout_id}",
                                f"payout.utr={p.utr}",
                                f"payout.amount_paise={p.amount_paise}",
                                "no_bank_match_within_7d=True",
                            ],
                            proposed_action="Locate missing bank settlement for processed payout",
                        )
                    )

        # 3. Classify Unmatched Banks (orphan bank, missing utr)
        for b in unmatched_banks:
            if b.bank_id in processed_banks:
                continue
            processed_banks.add(b.bank_id)

            if b.utr is None:
                raw_exceptions.append(
                    ReconException(
                        exception_id="temp",
                        row_ids=[b.bank_id],
                        bucket=ExceptionBucket.MISSING_UTR,
                        severity="high",
                        evidence=[
                            f"bank.bank_id={b.bank_id}",
                            "bank.utr=None",
                            f"bank.narration={b.narration}",
                            f"bank.amount_paise={b.amount_paise}",
                        ],
                        proposed_action="Extract reference from bank statement narration",
                    )
                )
            else:
                raw_exceptions.append(
                    ReconException(
                        exception_id="temp",
                        row_ids=[b.bank_id],
                        bucket=ExceptionBucket.ORPHAN_BANK,
                        severity="high",
                        evidence=[
                            f"bank.bank_id={b.bank_id}",
                            f"bank.amount_paise={b.amount_paise}",
                            f"bank.utr={b.utr}",
                            "no_payout_match=True",
                        ],
                        proposed_action="Trace credit with bank; no payout found within +/-7d",
                    )
                )

        # 4. Classify Unmatched Ledgers (orphan ledger, refund unpaired)
        for jrn_id, entries in unmatched_ledgers_by_jrn.items():
            if jrn_id in processed_journals:
                continue
            processed_journals.add(jrn_id)

            entry_ids = [e.ledger_id for e in entries]
            accounts = [e.account for e in entries]
            ref = entries[0].reference if entries else ""

            # Check if refund reversal (positive settlements_receivable or negative bank line)
            is_refund_reversal = any(
                (e.account == "settlements_receivable" and e.amount_paise > 0)
                or (e.account == "bank" and e.amount_paise < 0)
                for e in entries
            )

            if is_refund_reversal:
                raw_exceptions.append(
                    ReconException(
                        exception_id="temp",
                        row_ids=sorted(entry_ids),
                        bucket=ExceptionBucket.REFUND_UNPAIRED,
                        severity="medium",
                        evidence=[
                            f"journal_id={jrn_id}",
                            f"accounts={','.join(accounts)}",
                            f"reference={ref}",
                            "unpaired_reversal=True",
                        ],
                        proposed_action="Locate original settlement journal for refund reversal",
                    )
                )
            else:
                amt = sum(e.amount_paise for e in entries if e.amount_paise > 0)
                raw_exceptions.append(
                    ReconException(
                        exception_id="temp",
                        row_ids=sorted(entry_ids),
                        bucket=ExceptionBucket.ORPHAN_LEDGER,
                        severity="low",
                        evidence=[
                            f"journal_id={jrn_id}",
                            f"accounts={','.join(accounts)}",
                            f"reference={ref}",
                            f"amount_paise={amt}",
                        ],
                        proposed_action="Investigate unbalanced or unlinked ledger journal set",
                    )
                )

        # Deterministic sorting: sort by bucket value and first row_id
        def sort_key(ex: ReconException) -> tuple[str, str]:
            first_row = ex.row_ids[0] if ex.row_ids else ""
            return (ex.bucket.value, first_row)

        sorted_exceptions = sorted(raw_exceptions, key=sort_key)

        # Assign deterministic exception IDs: EX-0001, EX-0002, ...
        final_exceptions: list[ReconException] = []
        for idx, ex in enumerate(sorted_exceptions, start=1):
            final_exceptions.append(ex.model_copy(update={"exception_id": f"EX-{idx:04d}"}))

        return final_exceptions
