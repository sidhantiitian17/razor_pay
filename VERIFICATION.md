# Verification Guide & Test Execution

This document provides exact commands to independently verify every check, contract, and metric in the reconciliation engine.

---

## 1. Automated Full-Regression Suite

To execute all checks across all phases (P0 through P13) in a single pass:

```bash
bash scripts/checks/all.sh
```

Expected output:
```text
=== Running P0.sh === ... PHASE PASSED
=== Running P1.sh === ... PHASE PASSED
=== Running P2.sh === ... PHASE PASSED
=== Running P3.sh === ... PHASE PASSED
=== Running P4.sh === ... PHASE PASSED
=== Running P5.sh === ... PHASE PASSED
=== Running P6.sh === ... PHASE PASSED
=== Running P12.sh === ... PHASE PASSED
=== Running P13.sh === ... PHASE PASSED
ALL PHASES PASSED
```

---

## 2. Phase-by-Phase Verification Run

| Phase | Description | Command | Key Invariant / Pass Criteria |
|---|---|---|---|
| **P0** | Contracts, Schema, Models | `bash scripts/checks/P0.sh` | Strict typing, frozen models, valid schemas |
| **P1** | Synthetic Generator & Truth | `bash scripts/checks/P1.sh` | Seed stability, balanced journals, no real UTRs |
| **P2** | Blocker, Matcher, Baseline | `bash scripts/checks/P2.sh` | Blocker recall == 1.0, clean recall == 1.0 |
| **P3** | Agent Loop & Guardrail | `bash scripts/checks/P3.sh` | Replay determinism, guardrail coverage, no truth leak |
| **P4** | Classifier & State Closer | `bash scripts/checks/P4.sh` | 9-bucket reachability, dry-run, closure reversal |
| **P5** | Grader & Evaluation Sweep | `bash scripts/checks/P5.sh` | 4-arm ablation lift, 6 negative controls, worst-seed bar |
| **P6** | Persistence, Worker, Pub | `bash scripts/checks/P6.sh` | Zero secret leak, atomic row claim, idempotent write |
| **P7** | Shell & A11y Verification | `(cd ui && bun x playwright test tests_ui/shell.spec.ts tests_ui/a11y.spec.ts)` | WCAG AA compliance, responsive layout, theme toggle |
| **P8** | Dashboard No-Fabrication | `(cd ui && bun x playwright test tests_ui/no_fabrication.spec.ts)` | Zero fabricated KPI values against published report |
| **P9** | Workqueue & Triage Evidence | `(cd ui && bun x playwright test tests_ui/drilldown.spec.ts tests_ui/evidence.spec.ts tests_ui/workqueue_count.spec.ts)` | Source row drilldown, >=2 evidence strings per row |
| **P10** | Trace & Anti-Slop Verify | `(cd ui && bun x playwright test tests_ui/anti_slop.spec.ts)` | 8 anti-slop checks verified live on DOM |
| **P11** | Eval Lab & Holdout Gate | `bash scripts/checks/P11.sh` | Worst holdout seed matches gate value, dev seeds labelled tuning |
| **P12** | Live Wiring Integration | `bash scripts/checks/P12.sh` | DOM-vs-JSON crosscheck, triage isolation, 2nd-pass convergence |
| **P13** | Hardening, Security, Docs | `bash scripts/checks/P13.sh` | File sizes, doc links, static analysis, audit zero-leak |


---

## 3. Core Static Analysis & Security Audits

### 3.1 Unit Testing & Code Coverage
```bash
uv run pytest --cov=engine --cov-fail-under=85
```

### 3.2 Strict Type Checking
```bash
uv run mypy --strict engine
```

### 3.3 Formatting & Linting
```bash
uv run ruff check engine tests
uv run ruff format --check engine tests
```

### 3.4 Import Contract Boundary
```bash
uv run lint-imports
```

### 3.5 Secret & Credential Scanning
```bash
gitleaks detect --no-git
```

### 3.6 Dependency Vulnerability Audit
```bash
uv run pip-audit
```

---

## 4. Live Verification Tools

### 4.1 Crosscheck Published Run against Database
```bash
uv run python -m engine.tools.crosscheck --run <run_id>
```

### 4.2 Crosscheck Negative Controls
```bash
uv run python -m engine.tools.crosscheck --controls
```

### 4.3 Multi-Seed Evaluation Sweep
```bash
uv run python -m engine.eval.sweep --seeds 101-120
```

### 4.4 Four-Arm Ablation Analysis
```bash
uv run python -m engine.eval.ablation --seeds 101-120
```
