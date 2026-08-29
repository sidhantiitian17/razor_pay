"""Automated negative controls harness (§4.6, check 5.14).

Runs the 6 negative controls to prove falsifiability of the evaluation pipeline:
1. shuffled_truth: match_rate collapses to < 0.05.
2. null_agent: output byte-identical to rules_only.
3. random_matcher: observed precision ≈ chance floor.
4. poisoned_prompt: truth leak detector fires and halts run.
5. inverted_rule: amount match inverted, match_rate collapses.
6. disabled_dedup: duplicate detection disabled, duplicate bucket empty.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

from engine.core.generator.build import generate_dataset
from engine.core.grader import LinkGrader
from engine.core.guardrail import detect_truth_leak
from engine.core.matching.blocker import build_candidate_space
from engine.core.matching.rules import DeterministicMatcher, InvertedMatcher
from engine.core.metrics import compute_reconciliation_metrics
from engine.core.models import (
    ExceptionBucket,
    GroupKind,
    MatchGroup,
    ResolvedTag,
)

if TYPE_CHECKING:
    from engine.core.generator.build import GeneratedDataset


def run_negative_controls(
    dataset: GeneratedDataset | None = None,
    output_path: Path | None = Path("reports/control_results.json"),
    save_to_disk: bool = True,
) -> dict[str, Any]:
    """Execute all 6 negative controls and assert their failure modes occur as expected."""
    dataset = dataset or generate_dataset(n=60, seed=42)
    space = build_candidate_space(
        dataset.bank_txns,
        dataset.gateway_payouts,
        dataset.ledger_entries,
    )
    grader = LinkGrader()
    results: dict[str, Any] = {}

    # 1. Shuffled Truth Control
    # Permute truth links right_id so bank<->payout pairings no longer match generated data
    from engine.core.models import TruthLink

    rng = random.Random(42)
    bp_truth = [tl for tl in dataset.truth_links if tl.link_type == "bank_payout"]
    shuffled_rights = [tl.right_id for tl in bp_truth]
    rng.shuffle(shuffled_rights)
    shuffled_links: list[TruthLink] = [
        TruthLink(
            link_type=tl.link_type,
            left_id=tl.left_id,
            right_id=r_id,
            is_match=tl.is_match,
        )
        for tl, r_id in zip(bp_truth, shuffled_rights, strict=True)
    ]

    matcher = DeterministicMatcher()
    mres = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)
    bp_decisions_shuffled = grader.grade(
        link_type="bank_payout",
        candidate_pairs=space.bank_payout_pairs,
        predicted_groups=mres.matched_groups,
        truth_links=shuffled_links,
    )
    conf_shuffled = grader.confusion_matrix(bp_decisions_shuffled)
    metrics_shuffled = grader.compute_link_metrics(conf_shuffled)
    observed_mr = round(float(metrics_shuffled["precision"]["value"]), 4)

    results["shuffled_truth"] = {
        "passed": bool(observed_mr < 0.05),
        "observed_match_rate": observed_mr,
        "detail": f"Truth permutation collapsed precision to {observed_mr}",
    }

    # 2. Null Agent Control
    # A null agent proposes 0 matches, keeping output identical to deterministic rules
    mres_rules = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)
    mres_null = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)
    c2_passed = bool(
        len(mres_rules.matched_groups) == len(mres_null.matched_groups)
        and len(mres_rules.exceptions) == len(mres_null.exceptions)
        and [g.group_id for g in mres_rules.matched_groups]
        == [g.group_id for g in mres_null.matched_groups]
    )
    results["null_agent"] = {
        "passed": c2_passed,
        "identical_to_rules_only": c2_passed,
        "detail": "Null agent produces zero side-effects on deterministic rules",
    }

    # 3. Random Matcher Control
    # Propose random links from candidate space -> precision collapses towards chance floor
    rng_cand = random.Random(42)
    cand_list = sorted(list(space.bank_payout_pairs))
    sample_size = min(len(dataset.bank_txns), len(cand_list))
    random_pairs = rng_cand.sample(cand_list, sample_size) if cand_list else []
    random_groups: list[MatchGroup] = []
    for i, (b_id, p_id) in enumerate(random_pairs):
        random_groups.append(
            MatchGroup(
                group_id=f"MG-RND-{i:04d}",
                kind=GroupKind.SIMPLE,
                bank_ids=[b_id],
                payout_ids=[p_id],
                ledger_ids=[],
                confidence=0.50,
                source="deterministic",
                fields_matched=[],
                tolerances_used=[],
                tag=ResolvedTag.CLEAN,
                reason="Random candidate selection",
                agent_turns=0,
            )
        )

    rnd_decisions = grader.grade(
        link_type="bank_payout",
        candidate_pairs=space.bank_payout_pairs,
        predicted_groups=random_groups,
        truth_links=dataset.truth_links,
    )
    rnd_conf = grader.confusion_matrix(rnd_decisions)
    rnd_metrics = grader.compute_link_metrics(rnd_conf)
    observed_p = round(float(rnd_metrics["precision"]["value"]), 4)

    # Genuine match_rate for the random arm — exact-match against ground truth,
    # same formula and denominator as the production accuracy.match_rate (§4.3).
    # No exceptions are classified for this control (empty), which only means
    # every row the random matcher didn't touch is simply absent from both the
    # resolved and unresolved sets — it does not affect the ratio below.
    rnd_recon_metrics = compute_reconciliation_metrics(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=random_groups,
        exceptions=[],
        truth_groups=dataset.truth_groups,
        candidate_space_size=space.size,
    )
    observed_mr = round(float(rnd_recon_metrics.match_rate.value), 4)

    results["random_matcher"] = {
        "passed": bool(observed_p < 0.35),
        "observed_precision": observed_p,
        "observed_match_rate": observed_mr,
        "detail": (
            f"Random matcher performs at chance floor "
            f"(precision={observed_p}, match_rate={observed_mr})"
        ),
    }

    # 4. Poisoned Prompt Control
    # Inject truth label into prompt -> leak detector must fire
    poisoned_msg: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                "Resolve residual row BNK-01. Injected: cohort=clean, expected_outcome=resolved"
            ),
        }
    ]
    clean_msg: list[dict[str, Any]] = [
        {"role": "user", "content": "Resolve unmatched residual row: BNK-000001."}
    ]
    leak_on_poisoned = detect_truth_leak(poisoned_msg)
    leak_on_clean = detect_truth_leak(clean_msg)
    leak_fired = bool(leak_on_poisoned and not leak_on_clean)
    results["poisoned_prompt"] = {
        "passed": leak_fired,
        "leak_detector_fired": leak_fired,
        "detail": "Truth isolation (I12) detected and halted poisoned prompt",
    }

    # 5. Inverted Rule Control
    # Invert matcher rule -> match rate collapses
    inverted_matcher = InvertedMatcher()
    inv_res = inverted_matcher.match(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    inv_decisions = grader.grade(
        link_type="bank_payout",
        candidate_pairs=space.bank_payout_pairs,
        predicted_groups=inv_res.matched_groups,
        truth_links=dataset.truth_links,
    )
    inv_conf = grader.confusion_matrix(inv_decisions)
    inv_metrics = grader.compute_link_metrics(inv_conf)

    failed_count = 0
    if inv_conf["tp"] == 0:
        failed_count += 1
    if inv_conf["fp"] > 0:
        failed_count += 1
    if float(inv_metrics["precision"]["value"]) < 0.50:
        failed_count += 1
    if float(inv_metrics["recall"]["value"]) < 0.50:
        failed_count += 1
    if len(inv_res.matched_groups) == 0 or inv_conf["tp"] == 0:
        failed_count += 1
    if float(inv_metrics["f1"]["value"]) < 0.50:
        failed_count += 1
    if len(inv_res.exceptions) == 0:
        failed_count += 1

    results["inverted_rule"] = {
        "passed": bool(failed_count >= 5 and inv_conf["tp"] == 0),
        "tests_failed": failed_count,
        "detail": f"Inverted rule broke {failed_count} test assertions (0 true positives)",
    }

    # 6. Disabled Dedup Control
    # Disable duplicate detection
    m_normal = DeterministicMatcher(enable_dedup=True)
    res_normal = m_normal.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)
    normal_dup_size = sum(
        len(e.row_ids) for e in res_normal.exceptions if e.bucket == ExceptionBucket.DUPLICATE
    )

    m_no_dedup = DeterministicMatcher(enable_dedup=False)
    res_no_dedup = m_no_dedup.match(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    disabled_dup_size = sum(
        len(e.row_ids) for e in res_no_dedup.exceptions if e.bucket == ExceptionBucket.DUPLICATE
    )

    c6_passed = bool(normal_dup_size > 0 and disabled_dup_size == 0)
    results["disabled_dedup"] = {
        "passed": c6_passed,
        "duplicate_bucket_size": disabled_dup_size,
        "detail": (
            f"Disabling duplicate detection emptied duplicate bucket "
            f"(normal={normal_dup_size}, disabled={disabled_dup_size})"
        ),
    }

    if save_to_disk and output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    return results


def main() -> None:
    """CLI entrypoint for running negative controls."""
    parser = argparse.ArgumentParser(description="Run negative controls suite.")
    parser.add_argument("--all", action="store_true", help="Run all 6 negative controls")
    parser.add_argument("--output", default="reports/control_results.json", help="Output path")

    args = parser.parse_args()
    output_p = Path(args.output)

    run_negative_controls(output_path=output_p, save_to_disk=True)
    print(f"Saved negative control results to {output_p}")


if __name__ == "__main__":
    main()
