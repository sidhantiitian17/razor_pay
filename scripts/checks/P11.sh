#!/usr/bin/env bash
set -euo pipefail

echo "=== Running P11.sh ==="

# Check 11.2: Worst seed gate in Eval Lab
(cd ui && bun x playwright test tests_ui/worst_seed.spec.ts)
echo "PASS 11.2 worst_seed_gate"

# Check 11.3: Dev seeds separated and labelled "tuning -- not a claim"
(cd ui && bun x playwright test tests_ui/seed_set_labels.spec.ts)
echo "PASS 11.3 seed_set_labels"

echo "PHASE PASSED"
