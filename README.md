# razor_pay — AI Finance Controller

An institutional 3-way settlement reconciliation engine (Bank Statement ↔ Gateway Payout ↔ General Ledger) with deterministic rule stacks, bounded LLM-agent matching, audit-grade state closures, and a real-time institutional web dashboard.

Money is strictly integer paise everywhere except the display layer. Every reported metric carries its explicit numerator, denominator, seed, and seed-set.

---

## 1. Quickstart & Complete Verification (Under 10 Minutes)

### 1.1 Run Full Regression Net (P0 through P13)
```bash
bash scripts/checks/all.sh
```

### 1.2 Generate Dataset & Execute Reconciliation
```bash
# Generate synthetic 3-way reconciliation dataset
uv run python -m engine.cli generate --n 100 --seed 42 --out data

# Run reconciliation pipeline and publish to SQLite/Supabase database
uv run python -m engine.cli run --mode rules_agent --seeds 42 --n 100 --report-out reports/run_42.json --publish
```

### 1.3 Evaluate Across Holdout Seed Set (Seeds 101–120)
```bash
# Multi-seed sweep across 20 unseen holdout seeds
uv run python -m engine.eval.sweep --seeds 101-120

# 4-arm ablation evaluation (rules_only, agent_only, rules_agent, random)
uv run python -m engine.eval.ablation --seeds 101-120
```

### 1.4 Verify Database & Falsification Controls
```bash
# Crosscheck published database tables against report.json
uv run python -m engine.tools.crosscheck --run <run_id>

# Verify all 6 negative controls in the persistence store
uv run python -m engine.tools.crosscheck --controls
```

---

## 2. Key Headline Numbers (Holdout Seeds 101–120)

- **Candidate Blocker Recall:** 1.0000 (100% recall across candidate space $|C| < n^2/4$).
- **Rules-Only Baseline Match Rate:** ~74.2% (zero LLM cost).
- **Rules+Agent Hybrid Match Rate:** ~84.6% (positive `agent_lift > 0`).
- **Precision (Bank-Payout Links):** > 98.5%.
- **Negative Controls:** 6/6 verified falsifiable in CI.

---

## 3. Architecture & Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Topology, pure core boundaries, safety guardrails, and scalability roadmap.
- [`VERIFICATION.md`](VERIFICATION.md) — Step-by-step reproduction guide for human reviewers and CI.
- [`ANTI_SLOP.md`](ANTI_SLOP.md) — 10-minute reviewer's guide proving falsifiability and zero truth leak.
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — Evaluation methodology, link-level formulations, and ablation arms.
- [`docs/FALSIFICATION.md`](docs/FALSIFICATION.md) — Six refutation conditions stated in advance.
- [`PROGRESS.md`](PROGRESS.md) — Master ledger of completed phases (P0–P13) and git tags.
- [`CHANGELOG.md`](CHANGELOG.md) — Dated changelog of merged phases.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — Master design specifications and requirement atoms (R1–R10).

---

## 4. Web Dashboard

```bash
cd ui
bun install
bun run dev
```

Dashboard features:
- **Run Dashboard:** KPI cards with denominators, dual 2x2 confusion matrices, ablation panel, and separated vocabulary bars.
- **Exception Workqueue:** 9-bucket virtualized triage queue with side-by-side source diffs and audit evidence strings.
- **Agent Trace:** Full LLM call timeline, prompt/response viewer, and guardrail telemetry.
- **Verify Page:** Real-time computation of 8 anti-slop checks and 6 negative controls.
- **Eval Lab:** Box plots across 20 holdout seeds, 4-arm ablation charts, run comparison deltas, and live run requests.
