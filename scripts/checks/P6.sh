#!/usr/bin/env bash
set -euo pipefail

echo "=== Running P6.sh ==="

# Check 6.1: Publish then read back yields identical report.json
uv run pytest tests/test_publisher.py::test_round_trip -q
echo "PASS 6.1 publisher_round_trip"

# Check 6.2: No published row contains API key, auth header, or truth label
uv run pytest tests/test_publisher.py::test_no_secrets -q
echo "PASS 6.2 no_secrets_published"

# Check 6.3: Re-publishing the same run_id updates, never duplicates
uv run pytest tests/test_publisher.py::test_idempotent -q
echo "PASS 6.3 publisher_idempotent"

# Check 6.4: Two concurrent workers never claim the same request (row lock)
uv run pytest tests/test_worker.py::test_claim -q
echo "PASS 6.4 worker_claim_row_lock"

# Check 6.5: A failing run marks failed with message; never hangs in claimed
uv run pytest tests/test_worker.py::test_failure_path -q
echo "PASS 6.5 worker_failure_path"

# Check 6.6: Anon writes denied on every table
uv run pytest tests/test_rls.py::test_anon_cannot_write -q
echo "PASS 6.6 rls_anon_cannot_write"

# Check 6.7: CLI run --publish populates tables matching report.json
uv run pytest tests/test_publisher.py::test_cli_publish_row_counts -q
echo "PASS 6.7 cli_publish_counts"

# Check 6.8: control_results populated for all 6 controls
uv run pytest tests/test_publisher.py::test_controls_published -q
echo "PASS 6.8 controls_published"

echo "PHASE PASSED"
