"""Hardening and full coverage test suite (§9 P13, checks 13.1-13.13)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner
from engine.cli import main
from engine.config import ENGINE_VERSION, GUARDRAIL_MIN_CONFIDENCE, SCHEMA_VERSION
from engine.eval.ablation import run_ablation
from engine.eval.bench import run_benchmark
from engine.eval.sweep import run_sweep
from engine.eval.threshold import main as threshold_main
from engine.ports.clock import SystemClock
from engine.tools.check_docs import check_docs
from engine.tools.check_docs import main as check_docs_main
from engine.tools.check_file_sizes import check_file_sizes
from engine.tools.check_file_sizes import main as check_file_sizes_main
from engine.tools.validate_schema import main as validate_schema_main

if TYPE_CHECKING:
    from pathlib import Path


def test_check_file_sizes_tool() -> None:
    """Check 13.10: check_file_sizes tool passes on engine."""
    violations = check_file_sizes()
    assert violations == []
    check_file_sizes_main()


def test_check_docs_tool() -> None:
    """Check 13.12: check_docs tool passes on repo markdown files."""
    errors = check_docs()
    assert errors == []
    check_docs_main()


def test_validate_schema_tool() -> None:
    """Test validate_schema tool main."""
    validate_schema_main()


def test_system_clock() -> None:
    """Test SystemClock port implementation."""
    clock = SystemClock()
    t = clock.now()
    assert t.tzinfo is not None


def test_config_loader() -> None:
    """Test config constants."""
    assert ENGINE_VERSION == "0.1.0"
    assert SCHEMA_VERSION == "1.0.0"
    assert GUARDRAIL_MIN_CONFIDENCE == 0.70


def test_cli_commands(tmp_path: Path) -> None:
    """Test full coverage on CLI commands (generate, run, worker, compare, close)."""
    runner = CliRunner()

    # 1. generate
    res_gen = runner.invoke(
        main,
        ["generate", "--n", "60", "--seed", "42", "--out", str(tmp_path)],
    )
    assert res_gen.exit_code == 0

    # 2. run
    report_file = tmp_path / "test_report.json"
    res_run = runner.invoke(
        main,
        [
            "run",
            "--mode",
            "rules_only",
            "--seeds",
            "42",
            "--n",
            "60",
            "--report-out",
            str(report_file),
            "--publish",
        ],
    )
    assert res_run.exit_code == 0
    assert report_file.exists()

    # 3. worker --once
    res_worker = runner.invoke(main, ["worker", "--once", "--db", str(tmp_path / "test.db")])
    assert res_worker.exit_code == 0

    # 4. compare
    report_b = tmp_path / "test_report_b.json"
    report_b.write_text(report_file.read_text(encoding="utf-8"), encoding="utf-8")
    res_cmp = runner.invoke(main, ["compare", str(report_file), str(report_b)])
    assert res_cmp.exit_code == 0

    # 5. close & close --reverse
    res_close = runner.invoke(main, ["close", "--dry-run", "--db", str(tmp_path / "test.db")])
    assert res_close.exit_code == 0
    res_rev = runner.invoke(
        main,
        ["close", "--reverse", "run-test-1", "--db", str(tmp_path / "test.db")],
    )
    assert res_rev.exit_code == 0


def test_eval_modules(tmp_path: Path) -> None:
    """Test benchmark, ablation, sweep, and threshold execution."""
    # 1. Bench
    bench_res = run_benchmark(runs=1, concurrencies=[1], n=60)
    assert "concurrency_results" in bench_res
    assert bench_res["runs"] == 1

    # 2. Ablation
    ab_res = run_ablation(seeds=[42], n=60)
    assert "arms" in ab_res
    assert "rules_only" in ab_res["arms"]

    # 3. Sweep
    sw_res = run_sweep(seeds=[42], n=60)
    assert "runs" in sw_res
    assert "summary" in sw_res

    # 4. Threshold runner
    runner = CliRunner()
    th_out = tmp_path / "thresh.json"
    res_th = runner.invoke(threshold_main, ["--seeds", "42", "--output", str(th_out)])
    assert res_th.exit_code == 0
