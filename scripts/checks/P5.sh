#!/usr/bin/env bash
set -uo pipefail
export PYTHONUTF8=1
fails=0
check() {
  local id="$1" name="$2"; shift 2
  if out=$("$@" 2>&1); then
    echo "PASS $id $name"
  else
    echo "FAIL $id $name :: $(echo "$out" | grep -m1 -E 'Error|assert|FAILED|error' || echo "$out" | tail -1)"
    fails=$((fails+1))
  fi
}

check 5.1 report_schema         uv run pytest tests/test_report.py::test_schema -q
check 5.2 grader_hand_computed  uv run pytest tests/test_grader.py::test_hand_computed -q
check 5.3 report_denominators   uv run pytest tests/test_report.py::test_denominators -q
check 5.4 totals_reconcile      uv run pytest tests/test_report.py::test_totals_reconcile -q
check 5.5 sweep_harness         bash -c 'uv run python -m engine.eval.sweep --seeds 101-120 --n 100 && test -s reports/sweep.json'
check 5.6 worst_seed_bar        uv run pytest tests/test_eval.py::test_worst_seed_bar -q
check 5.7 ablation_harness      bash -c 'uv run python -m engine.eval.ablation --seeds 101-120 && test -s reports/ablation.json'
check 5.8 variance_band         uv run pytest tests/test_eval.py::test_variance_band -q
check 5.9 cli_compare           uv run python -m engine.cli compare reports/baseline.json reports/ablation.json
check 5.10 replay_regression    uv run pytest tests/test_regression.py -q
check 5.11 live_bench           bash -c 'uv run python -m engine.eval.bench --live --runs 3 --concurrency 1,4,8 && test -s reports/bench.json'
check 5.12 exception_evidence   uv run pytest tests/test_report.py::test_exception_evidence -q
check 5.13 stage_timings        uv run pytest tests/test_report.py::test_stage_seconds -q
check 5.14 negative_controls    bash -c 'uv run python -m engine.eval.controls --all && test -s reports/control_results.json'
check 5.15 holdout_hygiene      uv run pytest tests/test_eval.py::test_holdout_hygiene -q
check 5.16 grader_isolation     uv run pytest tests/test_grader.py::test_isolation -q

[ "$fails" -eq 0 ] || { echo "PHASE FAILED: $fails check(s)"; exit 1; }
echo "PHASE PASSED"
