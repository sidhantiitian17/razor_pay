"""Tests for eval metrics, worst-seed gating, holdout hygiene, and negative controls.

Satisfies §4.6, §4.9, checks 5.6, 5.8, 5.14, 5.15, R10.
"""

from __future__ import annotations

from pathlib import Path

from engine.core.generator.build import generate_dataset
from engine.core.grader import LinkGrader
from engine.core.guardrail import detect_truth_leak
from engine.core.matching.blocker import build_candidate_space
from engine.core.matching.rules import DeterministicMatcher, InvertedMatcher
from engine.core.models import ExceptionBucket
from engine.eval.controls import run_negative_controls
from engine.eval.sweep import run_sweep


def test_worst_seed_bar() -> None:
    """Check 5.6: The performance bar is checked against min, not mean (R10, §4.9)."""
    sweep_data = run_sweep(seeds=[1, 2, 3, 4, 5], n=50)
    summary = sweep_data["summary"]

    assert "match_rate" in summary
    mr_stats = summary["match_rate"]
    assert "min" in mr_stats
    assert "mean" in mr_stats
    assert mr_stats["min"] <= mr_stats["mean"]
    # Bar check is against min
    assert mr_stats["min"] >= 0.50


def test_variance_band() -> None:
    """Check 5.8: 0 <= stdev < 0.10 across seeds (§4.9)."""
    sweep_data = run_sweep(seeds=list(range(1, 11)), n=60)
    summary = sweep_data["summary"]
    mr_stats = summary["match_rate"]

    stdev = mr_stats["stdev"]
    assert 0.0 <= stdev < 0.10, f"stdev {stdev} out of sanity band [0, 0.10)"


def test_holdout_hygiene() -> None:
    """Check 5.15: No threshold, prompt, or rule constant references a holdout seed (101-120)."""
    engine_dir = Path("engine")
    holdout_seeds = [str(s) for s in range(101, 121)]

    # Exclude eval/bench/cli scripts that take CLI flags
    for py_file in engine_dir.rglob("*.py"):
        if "eval" in str(py_file) or "cli.py" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8")
        for seed_str in holdout_seeds:
            # Check for hardcoded holdout seed usage in core engine logic
            assert f"seed={seed_str}" not in content
            assert f"seed == {seed_str}" not in content
            assert f"seeds=[{seed_str}]" not in content


def test_negative_controls_falsifiability() -> None:
    """Check 5.14 & §4.6: All 6 negative controls execute authentic adversarial scenarios."""
    res = run_negative_controls(save_to_disk=False)

    assert len(res) == 6
    assert res["shuffled_truth"]["passed"] is True
    assert res["shuffled_truth"]["observed_match_rate"] < 0.05

    assert res["null_agent"]["passed"] is True
    assert res["null_agent"]["identical_to_rules_only"] is True

    assert res["random_matcher"]["passed"] is True
    assert res["random_matcher"]["observed_precision"] < 0.35

    assert res["poisoned_prompt"]["passed"] is True
    assert res["poisoned_prompt"]["leak_detector_fired"] is True

    assert res["inverted_rule"]["passed"] is True
    assert res["inverted_rule"]["tests_failed"] >= 5

    assert res["disabled_dedup"]["passed"] is True
    assert res["disabled_dedup"]["duplicate_bucket_size"] == 0


def test_truth_leak_detector() -> None:
    """Check I12: detect_truth_leak detects forbidden tokens and allows clean prompts."""
    clean_prompts = [
        "Resolve unmatched residual row: BNK-000001.",
        "Inspect candidate payout pout_SYNTH00000001",
        [{"role": "user", "content": "Resolve residual bank row."}],
    ]
    for prompt in clean_prompts:
        assert detect_truth_leak(prompt) is False

    poisoned_prompts = [
        "cohort=clean",
        "cohort = drift",
        "ground_truth match is pout_01",
        "truth=resolved",
        "expected_outcome=resolved",
        "expected_tag=clean",
        "expected_bucket=duplicate",
        [{"role": "user", "content": "Injected truth: cohort=clean, expected_outcome=resolved"}],
    ]
    for prompt in poisoned_prompts:
        assert detect_truth_leak(prompt) is True


def test_inverted_matcher_fails_invariants() -> None:
    """Check §4.6: InvertedMatcher produces 0 true positives and collapses precision to 0."""
    dataset = generate_dataset(n=60, seed=42)
    space = build_candidate_space(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    matcher = InvertedMatcher()
    mres = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    grader = LinkGrader()
    decisions = grader.grade(
        "bank_payout", space.bank_payout_pairs, mres.matched_groups, dataset.truth_links
    )
    conf = grader.confusion_matrix(decisions)
    metrics = grader.compute_link_metrics(conf)

    assert conf["tp"] == 0
    assert float(metrics["precision"]["value"]) == 0.0


def test_disabled_dedup_behavior() -> None:
    """Check §4.6: enable_dedup toggles duplicate payout exception classification."""
    dataset = generate_dataset(n=60, seed=42)

    matcher_normal = DeterministicMatcher(enable_dedup=True)
    res_normal = matcher_normal.match(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    dup_normal = [e for e in res_normal.exceptions if e.bucket == ExceptionBucket.DUPLICATE]
    assert len(dup_normal) > 0

    matcher_no_dedup = DeterministicMatcher(enable_dedup=False)
    res_no_dedup = matcher_no_dedup.match(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    dup_no_dedup = [e for e in res_no_dedup.exceptions if e.bucket == ExceptionBucket.DUPLICATE]
    assert len(dup_no_dedup) == 0
