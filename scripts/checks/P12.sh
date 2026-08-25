#!/usr/bin/env bash
set -euo pipefail

echo "=== Running P12.sh ==="

# Check 12.1: Run request lifecycle executed by worker
uv run pytest tests/test_live_wiring.py::test_run_request_worker_lifecycle -q
echo "PASS 12.1 run_request_worker_lifecycle"

# Check 12.2: Crosscheck tool verifies DOM/DB matches report.json
uv run pytest tests/test_live_wiring.py::test_crosscheck_tool_run -q
echo "PASS 12.2 crosscheck_tool_run"

# Check 12.3: Exception triage never mutates report.json
uv run pytest tests/test_live_wiring.py::test_triage_mutation_isolation -q
echo "PASS 12.3 triage_mutation_isolation"

# Check 12.4: close --reverse restores state and sets reversed_at
uv run pytest tests/test_live_wiring.py::test_cli_close_reverse -q
echo "PASS 12.4 close_reverse_state"

# Check 12.5: Smoke wiring and schema validation across endpoints
uv run pytest tests/test_live_wiring.py::test_smoke_wiring -q
echo "PASS 12.5 smoke_wiring"

# Check 12.6: Second pass convergence on closed state
uv run pytest tests/test_live_wiring.py::test_second_pass_convergence_live -q
echo "PASS 12.6 second_pass_convergence"

# Check 12.7: Crosscheck tool verifies negative controls in DB
uv run pytest tests/test_live_wiring.py::test_crosscheck_tool_controls -q
echo "PASS 12.7 crosscheck_tool_controls"

echo "PHASE PASSED"
