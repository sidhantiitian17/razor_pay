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

check 3.1 tool_schema          uv run pytest tests/test_agent.py::test_tool_schema -q
check 3.2 loop_bounded         uv run pytest tests/test_agent.py::test_loop_bounded -q
check 3.3 no_hallucinated_ids  uv run pytest tests/test_agent.py::test_no_hallucinated_ids -q
check 3.4 no_truth_leak        uv run pytest tests/test_agent.py::test_no_truth_leak -q
check 3.5 prompt_injection     uv run pytest tests/test_agent.py::test_prompt_injection -q
check 3.6 replay_determinism   uv run pytest tests/test_replay.py -q
check 3.7 guardrail_coverage   uv run pytest tests/test_guardrail.py -q --cov=engine/core/guardrail --cov-fail-under=95
check 3.8 threshold_sweep      bash -c 'uv run python -m engine.eval.threshold --seeds 1-10 && test -s reports/threshold_sweep.json'
check 3.9 cost_accounting      uv run pytest tests/test_agent.py::test_cost_accounting -q
check 3.10 cassette_secrets    bash -c '[ ! -d cassettes ] || [ $(grep -rEi "(authorization|x-api-key)" cassettes/ | wc -l) -eq 0 ]'
check 3.11 multi_turn          uv run pytest tests/test_agent.py::test_multi_turn -q
check 3.12 tool_ablation       uv run pytest tests/test_agent.py::test_tool_ablation -q
check 3.13 turn_stats          uv run pytest tests/test_agent.py::test_turn_stats -q

[ "$fails" -eq 0 ] || { echo "PHASE FAILED: $fails check(s)"; exit 1; }
echo "PHASE PASSED"
