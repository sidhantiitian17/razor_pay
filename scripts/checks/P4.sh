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

check 4.1 determinism          uv run pytest tests/test_classify.py::test_determinism -q
check 4.2 bucket_reachability  uv run pytest tests/test_classify.py::test_bucket_reachability -q
check 4.3 tag_reachability     uv run pytest tests/test_classify.py::test_tag_reachability -q
check 4.4 evidence             uv run pytest tests/test_classify.py::test_evidence -q
check 4.5 no_llm               uv run pytest tests/test_classify.py::test_no_llm -q
check 4.6 idempotent           uv run pytest tests/test_closer.py::test_idempotent -q
check 4.7 dry_run              uv run pytest tests/test_closer.py::test_dry_run -q
check 4.8 reversal             uv run pytest tests/test_closer.py::test_reversal -q
check 4.9 only_resolved        uv run pytest tests/test_closer.py::test_only_resolved -q
check 4.10 second_pass         uv run pytest tests/test_closer.py::test_second_pass -q
check 4.11 balanced            uv run pytest tests/test_closer.py::test_balanced -q

[ "$fails" -eq 0 ] || { echo "PHASE FAILED: $fails check(s)"; exit 1; }
echo "PHASE PASSED"
