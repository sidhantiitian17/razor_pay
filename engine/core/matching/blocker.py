"""Candidate space blocker (§4.2, checks 2.1, 2.2).

Constructs the explicit candidate universe `C` for link-level evaluation.
All true negatives are counted within `C`, and blocker recall caps the whole system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.core.models import BankTxn, GatewayPayout, LedgerEntry, TruthLink


@dataclass(frozen=True)
class MetricValue:
    """Standard metric representation with value, numerator, denominator (§4.3, I11)."""

    value: float
    numerator: int
    denominator: int

    def to_dict(self) -> dict[str, object]:
        """Convert metric to standard dict with rounded value."""
        return {
            "value": round(self.value, 4),
            "numerator": self.numerator,
            "denominator": self.denominator,
        }


@dataclass(frozen=True)
class CandidateSpace:
    """The explicit candidate link space C (§4.2)."""

    bank_payout_pairs: set[tuple[str, str]]
    payout_ledger_pairs: set[tuple[str, str]]

    @property
    def size(self) -> int:
        """Total number of candidate links |C|."""
        return len(self.bank_payout_pairs) + len(self.payout_ledger_pairs)


def build_candidate_space(
    bank_txns: list[BankTxn],
    gateway_payouts: list[GatewayPayout],
    ledger_entries: list[LedgerEntry],
) -> CandidateSpace:
    """Build candidate space C using blocking predicates (§4.2).

    Rules for bank <-> payout:
      - UTR equality (non-null)
      - Narration contains payout reference
      - Amount net within max(200, 1% of net)
      - Settled/Value date within 7 days AND amount within 10%

    Rules for payout <-> ledger:
      - Reference matching payout_id
      - Amount matching gross, net, fee, or tax within tolerance
    """
    bank_payout_pairs: set[tuple[str, str]] = set()

    for b in bank_txns:
        for p in gateway_payouts:
            # 1. UTR equality
            if b.utr is not None and p.utr is not None and b.utr == p.utr:
                bank_payout_pairs.add((b.bank_id, p.payout_id))
                continue

            # 2. Narration contains payout_id (recoverable UTR)
            if p.payout_id in b.narration:
                bank_payout_pairs.add((b.bank_id, p.payout_id))
                continue

            delta = abs(b.amount_paise - p.net_paise)
            # 3. Amount tolerance: within max(200, 1% of net_paise)
            tol = max(200, int(p.net_paise * 0.01))
            if delta <= tol:
                bank_payout_pairs.add((b.bank_id, p.payout_id))
                continue

            # 4. Date tolerance: within 7 days AND amount within 10%
            if p.settled_at is not None:
                days = abs((b.value_date - p.settled_at.date()).days)
                if days <= 7 and delta <= int(p.net_paise * 0.10):
                    bank_payout_pairs.add((b.bank_id, p.payout_id))

    payout_ledger_pairs: set[tuple[str, str]] = set()

    for p in gateway_payouts:
        for entry in ledger_entries:
            # 1. Reference matching
            if entry.reference == p.payout_id:
                payout_ledger_pairs.add((p.payout_id, entry.ledger_id))
                continue

            # 2. Amount matching gross, net, fee, or tax within tolerance
            gross_delta = abs(abs(entry.amount_paise) - p.amount_paise)
            net_delta = abs(entry.amount_paise - p.net_paise)
            fee_delta = abs(entry.amount_paise - p.fee_paise)
            tax_delta = abs(entry.amount_paise - p.tax_paise)
            if gross_delta <= 200 or net_delta <= 200 or fee_delta <= 200 or tax_delta <= 200:
                payout_ledger_pairs.add((p.payout_id, entry.ledger_id))

    return CandidateSpace(
        bank_payout_pairs=bank_payout_pairs,
        payout_ledger_pairs=payout_ledger_pairs,
    )


def evaluate_blocker_recall(
    space: CandidateSpace,
    truth_links: list[TruthLink],
) -> MetricValue:
    """Calculate blocker recall = true links inside C / total true links (§4.3)."""
    true_links = [t for t in truth_links if t.is_match]
    if not true_links:
        return MetricValue(value=1.0, numerator=0, denominator=0)

    hits = 0
    for t in true_links:
        in_bp = t.link_type == "bank_payout" and (t.left_id, t.right_id) in space.bank_payout_pairs
        in_pl = (
            t.link_type == "payout_ledger" and (t.left_id, t.right_id) in space.payout_ledger_pairs
        )
        if in_bp or in_pl:
            hits += 1

    recall_val = hits / len(true_links)
    return MetricValue(
        value=recall_val,
        numerator=hits,
        denominator=len(true_links),
    )
