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

check 2.1 blocker_recall         uv run pytest tests/test_blocker.py::test_recall -q
check 2.2 blocker_space_size     uv run pytest tests/test_blocker.py::test_space_size -q
check 2.3 zero_false_positives   uv run pytest tests/test_rules.py::test_zero_false_positives -q
check 2.4 clean_recall           uv run pytest tests/test_rules.py::test_clean_recall -q
check 2.5 duplicates_flagged     uv run pytest tests/test_rules.py::test_duplicates -q
check 2.6 refund_pairs_grouped   uv run pytest tests/test_rules.py::test_refund_pairs -q
check 2.7 tolerance_boundaries   uv run pytest tests/test_rules.py::test_tolerance_boundaries -q
check 2.8 outlier_attribution    uv run pytest tests/test_attribute.py -q
check 2.9 baseline_published     bash -c 'uv run python -m engine.cli run --mode rules_only --seeds 101-120 && test -s reports/baseline.json'
check 2.10 rates_sum_invariants  uv run pytest tests/test_metrics.py::test_rates_sum -q

[ "$fails" -eq 0 ] || { echo "PHASE FAILED: $fails check(s)"; exit 1; }
echo "PHASE PASSED"
