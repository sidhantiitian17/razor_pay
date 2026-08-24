"""Outlier attribution logic for 3-way reconciliation triads (§3.4, D3, check 2.8).

When three sources hold a value that should agree, the odd one out names the bucket:
  - bank outlier (drift > 50p, gross matches) -> AMOUNT_MISMATCH
  - payout fee outlier (fee perturbed, bank matches ledger) -> FEE_MISMATCH
  - ledger mismatch / break -> PARTIAL_GROUP
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.core.models import ExceptionBucket, ResolvedTag

if TYPE_CHECKING:
    from engine.core.models import BankTxn, GatewayPayout, LedgerEntry


def attribute_triad_outlier(
    bank: BankTxn,
    payout: GatewayPayout,
    ledgers: list[LedgerEntry],
) -> tuple[str, ResolvedTag | None, ExceptionBucket | None]:
    """Determine whether a triad is resolved or unresolved, and name the bucket.

    Args:
        bank: Bank credit transaction.
        payout: Gateway payout instruction.
        ledgers: List of ledger entries associated with this settlement.

    Returns:
        tuple of (verdict, resolved_tag, exception_bucket)
    """
    rec_entry = next((e for e in ledgers if e.account == "settlements_receivable"), None)
    bank_entry = next((e for e in ledgers if e.account == "bank"), None)
    fee_entry = next((e for e in ledgers if e.account == "gateway_fees"), None)
    tax_entry = next((e for e in ledgers if e.account == "gateway_tax"), None)

    if rec_entry is None or bank_entry is None or fee_entry is None or tax_entry is None:
        return ("unresolved", None, ExceptionBucket.PARTIAL_GROUP)

    if sum(e.amount_paise for e in ledgers) != 0:
        return ("unresolved", None, ExceptionBucket.PARTIAL_GROUP)

    # Check gross receivable agreement
    gross_agrees = abs(rec_entry.amount_paise) == payout.amount_paise
    if not gross_agrees:
        return ("unresolved", None, ExceptionBucket.PARTIAL_GROUP)

    # Case 1: Exact agreement across bank, payout net, and ledger bank line
    if bank.amount_paise == payout.net_paise == bank_entry.amount_paise:
        return ("resolved", ResolvedTag.CLEAN, None)

    drift = abs(bank.amount_paise - payout.net_paise)

    # Case 2: Tolerated drift (<= 50 paise) where ledger bank matches payout net
    if 1 <= drift <= 50 and payout.net_paise == bank_entry.amount_paise:
        return ("resolved", ResolvedTag.DRIFT, None)

    # Case 3: Excessive drift (bank is the outlier, ledger matches payout net)
    if drift > 50 and payout.net_paise == bank_entry.amount_paise:
        return ("unresolved", None, ExceptionBucket.AMOUNT_MISMATCH)

    # Case 4: Fee mismatch (payout fee is the outlier, bank matches ledger bank entry)
    if (
        payout.net_paise != bank.amount_paise
        and bank.amount_paise == bank_entry.amount_paise
        and payout.fee_paise != fee_entry.amount_paise
    ):
        return ("unresolved", None, ExceptionBucket.FEE_MISMATCH)

    # Case 5: Ledger break or general disagreement
    return ("unresolved", None, ExceptionBucket.PARTIAL_GROUP)
