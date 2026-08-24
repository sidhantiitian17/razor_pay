"""Tests for eval metrics, worst-seed gating, and holdout hygiene (checks 5.6, 5.8, 5.15, R10)."""

from pathlib import Path

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
    """Check 5.8: 0 < stdev < 0.10 across seeds (§4.9)."""
    sweep_data = run_sweep(seeds=list(range(1, 11)), n=60)
    summary = sweep_data["summary"]
    mr_stats = summary["match_rate"]

    stdev = mr_stats["stdev"]
    assert 0.0 < stdev < 0.10, f"stdev {stdev} out of sanity band (0, 0.10)"


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
