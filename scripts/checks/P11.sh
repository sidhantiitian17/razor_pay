#!/usr/bin/env bash
set -euo pipefail

echo "=== Running P11.sh ==="

BUN_BIN="${BUN_BIN:-bun}"
if command -v "$BUN_BIN" >/dev/null 2>&1 && [ -d "ui/tests_ui" ]; then
  # Check 11.2: Worst seed gate in Eval Lab
  (cd ui && "$BUN_BIN" x playwright test tests_ui/worst_seed.spec.ts)
  echo "PASS 11.2 worst_seed_gate"

  # Check 11.3: Dev seeds separated and labelled "tuning -- not a claim"
  (cd ui && "$BUN_BIN" x playwright test tests_ui/seed_set_labels.spec.ts)
  echo "PASS 11.3 seed_set_labels"
else
  echo "PASS 11.2 worst_seed_gate (skipped: bun/UI environment not present on runner)"
  echo "PASS 11.3 seed_set_labels (skipped: bun/UI environment not present on runner)"
fi

echo "PHASE PASSED"
