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

check 1.1 allocate_sum            uv run pytest tests/test_allocate.py -q
check 1.2 seed_stability          uv run pytest tests/test_generator.py::test_seed_stability -q
check 1.3 cross_seed_variance     uv run pytest tests/test_generator.py::test_cross_seed_variance -q
check 1.4 cohorts_disjoint        uv run pytest tests/test_cohorts.py::test_disjoint -q
check 1.5 truth_partition         uv run pytest tests/test_generator.py::test_truth_partition -q
check 1.6 journals_balance        uv run pytest tests/test_generator.py::test_journals_balance -q
check 1.7 no_real_utrs            uv run pytest tests/test_generator.py::test_no_real_utrs -q
check 1.8 cli_generate            bash -c 'uv run python -m engine.cli generate --n 60 --seed 42 && test $(wc -l < data/bank_txns.csv) -ge 50 && test $(wc -l < data/gateway_payouts.csv) -ge 50 && test $(wc -l < data/ledger_entries.csv) -ge 50'
check 1.9 terminal_states         uv run pytest tests/test_cohorts.py::test_terminal_states -q
check 1.10 outlier_attribution    uv run pytest tests/test_cohorts.py::test_attribution -q
check 1.11 bucket_generators      uv run pytest tests/test_generator.py::test_bucket_generators -q

[ "$fails" -eq 0 ] || { echo "PHASE FAILED: $fails check(s)"; exit 1; }
echo "PHASE PASSED"
