#!/usr/bin/env bash
# Regression net: runs all phase check runners up to the current phase.
set -uo pipefail
script_dir="$(cd "$(dirname "$0")" && pwd)"
fails=0

for script in "$script_dir"/P*.sh; do
  if [ -f "$script" ] && [ "$script" != "$0" ]; then
    echo "=== Running $(basename "$script") ==="
    if ! bash "$script"; then
      fails=$((fails+1))
    fi
    echo ""
  fi
done

[ "$fails" -eq 0 ] || { echo "REGRESSION FAILED: $fails phase(s)"; exit 1; }
echo "ALL PHASES PASSED"
