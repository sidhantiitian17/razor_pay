"""Evaluation grader emitting LinkDecision[] and link confusion matrices.

Satisfies §4.1, §4.2, R8, D6, check 5.2, 5.16.
Pure core module: isolated from rules and agent runner (check 5.16).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from engine.core.models import (
    LinkDecision,
    MatchGroup,
    TruthLink,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class LinkGrader:
    """Grader evaluating predicted match links against ground truth within candidate space."""

    def grade(
        self,
        link_type: Literal["bank_payout", "payout_ledger"],
        candidate_pairs: Sequence[tuple[str, str]] | set[tuple[str, str]],
        predicted_groups: list[MatchGroup],
        truth_links: list[TruthLink],
    ) -> list[LinkDecision]:
        """Grade candidate link pairs as TP, FP, FN, or TN against ground truth."""
        # Derive predicted link set
        predicted_set: set[tuple[str, str]] = set()
        for mg in predicted_groups:
            if link_type == "bank_payout":
                for b in mg.bank_ids:
                    for p in mg.payout_ids:
                        predicted_set.add((b, p))
            elif link_type == "payout_ledger":
                for p in mg.payout_ids:
                    for el in mg.ledger_ids:
                        predicted_set.add((p, el))

        # Build truth map
        truth_map: dict[tuple[str, str], bool] = {}
        for tl in truth_links:
            if tl.link_type == link_type:
                truth_map[(tl.left_id, tl.right_id)] = tl.is_match

        decisions: list[LinkDecision] = []
        for left, right in candidate_pairs:
            pred = (left, right) in predicted_set
            truth = truth_map.get((left, right), False)

            if pred and truth:
                outcome: Literal["TP", "FP", "FN", "TN"] = "TP"
            elif pred and not truth:
                outcome = "FP"
            elif not pred and truth:
                outcome = "FN"
            else:
                outcome = "TN"

            decisions.append(
                LinkDecision(
                    link_type=link_type,
                    left_id=left,
                    right_id=right,
                    predicted=pred,
                    truth=truth,
                    outcome=outcome,
                )
            )

        return decisions

    def confusion_matrix(self, decisions: list[LinkDecision]) -> dict[str, int]:
        """Compute confusion matrix counts from link decisions."""
        tp = sum(1 for d in decisions if d.outcome == "TP")
        fp = sum(1 for d in decisions if d.outcome == "FP")
        fn = sum(1 for d in decisions if d.outcome == "FN")
        tn = sum(1 for d in decisions if d.outcome == "TN")
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}

    def compute_link_metrics(self, confusion: dict[str, int]) -> dict[str, dict[str, float | int]]:
        """Compute precision, recall, and F1 with numerator and denominator (I11)."""
        tp = confusion["tp"]
        fp = confusion["fp"]
        fn = confusion["fn"]

        p_den = tp + fp
        p_val = (tp / p_den) if p_den > 0 else 0.0

        r_den = tp + fn
        r_val = (tp / r_den) if r_den > 0 else 0.0

        f1_den = p_val + r_val
        f1_val = (2 * p_val * r_val / f1_den) if f1_den > 0 else 0.0

        return {
            "precision": {"value": p_val, "numerator": tp, "denominator": p_den},
            "recall": {"value": r_val, "numerator": tp, "denominator": r_den},
            "f1": {"value": f1_val, "numerator": 2 * tp, "denominator": 2 * tp + fp + fn},
        }
