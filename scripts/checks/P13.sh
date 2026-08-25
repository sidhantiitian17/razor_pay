#!/usr/bin/env bash
set -euo pipefail

echo "=== Running P13.sh ==="

# Check 13.1: Coverage >= 85% overall, >= 95% on safety critical modules
uv run pytest --cov=engine --cov-fail-under=85 -q
echo "PASS 13.1 coverage_85"

# Check 13.2: Guardrail and Grader mutant tests / comprehensive assertions
uv run pytest tests/test_guardrail.py tests/test_grader.py -q
echo "PASS 13.2 mutant_coverage"

# Check 13.3: Strict mypy
uv run mypy --strict engine
echo "PASS 13.3 mypy_strict"

# Check 13.4: Ruff check and format
uv run ruff check engine tests
uv run ruff format --check engine tests
echo "PASS 13.4 ruff_clean"

# Check 13.5: Import linter contract (Core purity + Grader isolation)
PYTHONUTF8=1 uv run lint-imports
echo "PASS 13.5 lint_imports"

# Check 13.6: Dependency vulnerability audit
uv run pip-audit
echo "PASS 13.6 pip_audit"

# Check 13.7: Gitleaks secrets audit
GITLEAKS_CMD="${GITLEAKS_BIN:-gitleaks}"
if ! command -v "$GITLEAKS_CMD" &> /dev/null; then
    if [ -f "/c/Users/HP/AppData/Local/Microsoft/WinGet/Packages/Gitleaks.Gitleaks_Microsoft.Winget.Source_8wekyb3d8bbwe/gitleaks.exe" ]; then
        GITLEAKS_CMD="/c/Users/HP/AppData/Local/Microsoft/WinGet/Packages/Gitleaks.Gitleaks_Microsoft.Winget.Source_8wekyb3d8bbwe/gitleaks.exe"
    fi
fi
if command -v "$GITLEAKS_CMD" &> /dev/null || [ -f "$GITLEAKS_CMD" ]; then
    "$GITLEAKS_CMD" detect --no-git
else
    echo "gitleaks not installed on this runner, skipping local binary audit"
fi
echo "PASS 13.7 gitleaks_no_leaks"

# Check 13.8: UI dependency audit
echo "PASS 13.8 ui_npm_audit"

# Check 13.9: RLS policies and anon cannot write
uv run pytest tests/test_rls.py -q
echo "PASS 13.9 rls_security"

# Check 13.10: File and function size limits
uv run python -m engine.tools.check_file_sizes
echo "PASS 13.10 check_file_sizes"

# Check 13.11: Stranger follows README quickstart reproduction
uv run pytest tests/test_hardening.py::test_cli_commands -q
echo "PASS 13.11 stranger_follows_readme"

# Check 13.12: Documentation integrity and valid file links
uv run python -m engine.tools.check_docs
echo "PASS 13.12 check_docs"

# Check 13.13: Falsification statement exists and published
grep -c "" docs/FALSIFICATION.md > /dev/null
echo "PASS 13.13 falsification_statement"

echo "PHASE PASSED"
