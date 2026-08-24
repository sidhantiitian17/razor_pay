"""Reconciliation metrics calculation formulas and invariants (§4.3, I9, I10, I11, D5).

Computes link-level, group-level, and row-level reconciliation metrics with exact
numerators and denominators, ensuring no float is serialized without its denominator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from engine.core.matching.blocker import MetricValue

if TYPE_CHECKING:
    from engine.core.models import (
        BankTxn,
        GatewayPayout,
        LedgerEntry,
        MatchGroup,
        ReconException,
        TruthGroup,
    )


@dataclass(frozen=True)
class LinkMetrics:
    """Link-level confusion matrix and precision/recall/F1 (§4.1, §4.3)."""

    tp: int
    fp: int
    fn: int
    tn: int
    precision: MetricValue
    recall: MetricValue
    f1: float

    def to_dict(self) -> dict[str, object]:
        """Convert link metrics to standard serializable dictionary."""
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "precision": self.precision.to_dict(),
            "recall": self.recall.to_dict(),
            "f1": round(self.f1, 4),
        }


@dataclass(frozen=True)
class ReconciliationMetrics:
    """Complete accuracy and disposition metrics bundle."""

    match_rate: MetricValue
    resolved_rate: MetricValue
    unresolved_rate: MetricValue
    bank_payout_links: LinkMetrics
    payout_ledger_links: LinkMetrics

    def to_accuracy_dict(self) -> dict[str, object]:
        """Convert to accuracy block matching report.schema.json."""
        return {
            "match_rate": self.match_rate.to_dict(),
            "resolved_rate": self.resolved_rate.to_dict(),
            "unresolved_rate": self.unresolved_rate.to_dict(),
            "links": {
                "bank_payout": self.bank_payout_links.to_dict(),
                "payout_ledger": self.payout_ledger_links.to_dict(),
            },
        }


def _compute_link_metrics(
    true_pairs: set[tuple[str, str]],
    pred_pairs: set[tuple[str, str]],
    candidate_pairs: set[tuple[str, str]],
) -> LinkMetrics:
    """Compute confusion matrix and precision/recall/F1 for a link type within C."""
    tp = len(pred_pairs & true_pairs)
    fp = len(pred_pairs - true_pairs)
    fn = len(true_pairs - pred_pairs)
    tn = len(candidate_pairs - (pred_pairs | true_pairs))

    prec_den = tp + fp
    prec_val = tp / prec_den if prec_den > 0 else 1.0
    precision = MetricValue(value=prec_val, numerator=tp, denominator=prec_den)

    rec_den = tp + fn
    rec_val = tp / rec_den if rec_den > 0 else 1.0
    recall = MetricValue(value=rec_val, numerator=tp, denominator=rec_den)

    f1 = (2 * prec_val * rec_val) / (prec_val + rec_val) if (prec_val + rec_val) > 0 else 0.0

    return LinkMetrics(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def compute_reconciliation_metrics(
    bank_txns: list[BankTxn],
    gateway_payouts: list[GatewayPayout],
    ledger_entries: list[LedgerEntry],
    matched_groups: list[MatchGroup],
    exceptions: list[ReconException],
    truth_groups: list[TruthGroup],
    candidate_space_size: int,
) -> ReconciliationMetrics:
    """Compute all reconciliation metrics per §4.3 formulas."""
    total_source_rows = len(bank_txns) + len(gateway_payouts) + len(ledger_entries)

    # 1. Row-level resolved and unresolved rates
    resolved_rows = {
        rid for g in matched_groups for rid in g.bank_ids + g.payout_ids + g.ledger_ids
    }
    unresolved_rows = {rid for e in exceptions for rid in e.row_ids}

    # Ensure no rows are counted twice (I10)
    assert resolved_rows.isdisjoint(unresolved_rows)

    resolved_rate = MetricValue(
        value=len(resolved_rows) / total_source_rows if total_source_rows > 0 else 0.0,
        numerator=len(resolved_rows),
        denominator=total_source_rows,
    )
    unresolved_rate = MetricValue(
        value=len(unresolved_rows) / total_source_rows if total_source_rows > 0 else 0.0,
        numerator=len(unresolved_rows),
        denominator=total_source_rows,
    )

    # 2. Group-level match rate (exact set equality on all 3 ID lists and kind)
    exact_matches = 0
    truth_group_sets = {
        (
            g.kind,
            frozenset(g.bank_ids),
            frozenset(g.payout_ids),
            frozenset(g.ledger_ids),
        )
        for g in truth_groups
        if g.expected_outcome == "resolved"
    }

    for mg in matched_groups:
        pred_set = (
            mg.kind,
            frozenset(mg.bank_ids),
            frozenset(mg.payout_ids),
            frozenset(mg.ledger_ids),
        )
        if pred_set in truth_group_sets:
            exact_matches += 1

    total_truth_groups = len(truth_groups)
    match_rate = MetricValue(
        value=exact_matches / total_truth_groups if total_truth_groups > 0 else 0.0,
        numerator=exact_matches,
        denominator=total_truth_groups,
    )

    # 3. Link-level metrics
    true_bp: set[tuple[str, str]] = set()
    true_pl: set[tuple[str, str]] = set()

    for tg in truth_groups:
        if tg.expected_outcome == "resolved":
            if tg.bank_ids and tg.payout_ids:
                true_bp.add((tg.bank_ids[0], tg.payout_ids[0]))
            if tg.payout_ids and tg.ledger_ids:
                for lid in tg.ledger_ids:
                    true_pl.add((tg.payout_ids[0], lid))

    pred_bp: set[tuple[str, str]] = set()
    pred_pl: set[tuple[str, str]] = set()

    for mg in matched_groups:
        if mg.bank_ids and mg.payout_ids:
            pred_bp.add((mg.bank_ids[0], mg.payout_ids[0]))
        if mg.payout_ids and mg.ledger_ids:
            for lid in mg.ledger_ids:
                pred_pl.add((mg.payout_ids[0], lid))

    # Candidate spaces for TN calculation
    all_bp_cand = {(b.bank_id, p.payout_id) for b in bank_txns for p in gateway_payouts}
    all_pl_cand = {
        (p.payout_id, entry.ledger_id) for p in gateway_payouts for entry in ledger_entries
    }

    bp_metrics = _compute_link_metrics(true_bp, pred_bp, all_bp_cand)
    pl_metrics = _compute_link_metrics(true_pl, pred_pl, all_pl_cand)

    return ReconciliationMetrics(
        match_rate=match_rate,
        resolved_rate=resolved_rate,
        unresolved_rate=unresolved_rate,
        bank_payout_links=bp_metrics,
        payout_ledger_links=pl_metrics,
    )
