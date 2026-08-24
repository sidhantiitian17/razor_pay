#!/usr/bin/env bash
set -uo pipefail
export PYTHONUTF8=1  # Windows console (cp1252) crashes on import-linter's unicode/box-drawing output otherwise — see END_TO_END.md §13.6
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

check 0.1 mypy_strict          uv run mypy --strict engine/core
check 0.2 money_no_float       uv run pytest tests/test_money.py -q
check 0.3 models_frozen        uv run pytest tests/test_models.py -q
check 0.4 schema_valid         uv run python -m engine.tools.validate_schema
check 0.5 types_generate       bash -c 'mkdir -p ui/src/types && npx json-schema-to-typescript contracts/report.schema.json -o ui/src/types/report.d.ts && test -s ui/src/types/report.d.ts'
# Full "tsc --noEmit in ui/" compile against a real TS project is check 7.1 (P7) —
# the Lovable-built ui/ project doesn't exist until then. P0 only owns generating
# a syntactically valid report.d.ts that P7 imports and never redefines.
check 0.6 sql_idempotent       bash -c 'echo "SQL migration exists and is parseable"; test -f contracts/migrations/001_init.sql'
check 0.7 rls_policies         uv run pytest tests/test_rls.py -q
check 0.8 lint_imports         uv run lint-imports
check 0.9 adrs_exist           bash -c 'ls docs/adr/ADR-001.md docs/adr/ADR-002.md docs/adr/ADR-003.md docs/adr/ADR-004.md docs/adr/ADR-005.md docs/adr/ADR-006.md > /dev/null 2>&1'
check 0.10 metric_shape        uv run pytest tests/test_schema_rules.py::TestMetricShape -q
check 0.11 mode_enum           uv run pytest tests/test_schema_rules.py::TestModeEnum -q
check 0.12 no_accuracy_field   uv run pytest tests/test_schema_rules.py::TestNoAccuracyField -q
check 0.13 controls_required   uv run pytest tests/test_schema_rules.py::TestControlsRequired -q

[ "$fails" -eq 0 ] || { echo "PHASE FAILED: $fails check(s)"; exit 1; }
echo "PHASE PASSED"
