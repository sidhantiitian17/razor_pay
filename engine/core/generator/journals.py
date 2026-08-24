"""Balanced journal set construction (§3.3, D3, ADR-003).

Every journal set groups lines that must sum to exactly zero paise (I3).
The bank line is positive for cash received, negative for refunds.
Settlements receivable clears the gross payout. Fee and tax lines account
for the difference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.core.models import LedgerEntry

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date


def make_settlement_journal(
    journal_id: str,
    payout_id: str,
    gross_paise: int,
    fee_paise: int,
    tax_paise: int,
    entry_date: date,
    id_generator: Callable[[], str],
) -> list[LedgerEntry]:
    """Create a standard 4-line settlement journal set that sums to zero paise.

    Accounts:
      - settlements_receivable: -gross (credit clearing receivable)
      - bank: +net (debit cash received)
      - gateway_fees: +fee (debit expense)
      - gateway_tax: +tax (debit expense)
    """
    net_paise = gross_paise - fee_paise - tax_paise

    entries = [
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=-gross_paise,
            account="settlements_receivable",
            reference=payout_id,
        ),
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=net_paise,
            account="bank",
            reference=payout_id,
        ),
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=fee_paise,
            account="gateway_fees",
            reference=payout_id,
        ),
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=tax_paise,
            account="gateway_tax",
            reference=payout_id,
        ),
    ]

    assert sum(e.amount_paise for e in entries) == 0
    return entries


def make_refund_reversal_journal(
    journal_id: str,
    payout_id: str,
    gross_paise: int,
    fee_paise: int,
    tax_paise: int,
    entry_date: date,
    id_generator: Callable[[], str],
) -> list[LedgerEntry]:
    """Create an offsetting 4-line refund reversal journal set summing to zero."""
    net_paise = gross_paise - fee_paise - tax_paise

    entries = [
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=gross_paise,
            account="settlements_receivable",
            reference=payout_id,
        ),
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=-net_paise,
            account="bank",
            reference=payout_id,
        ),
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=-fee_paise,
            account="gateway_fees",
            reference=payout_id,
        ),
        LedgerEntry(
            ledger_id=id_generator(),
            journal_id=journal_id,
            entry_date=entry_date,
            amount_paise=-tax_paise,
            account="gateway_tax",
            reference=payout_id,
        ),
    ]

    assert sum(e.amount_paise for e in entries) == 0
    return entries
