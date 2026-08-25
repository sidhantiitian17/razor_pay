# Reviewer's 10-Minute Anti-Slop Guide

This guide is designed for external reviewers, auditors, and interviewers to verify within 10 minutes that this system is a legitimate financial engineering artifact rather than prompt-engineered demo code.

---

## 1. Five-Second Refutation Checks

If any of the following 5 tests fail, the project is refuted:

1. **No Truth Leak in LLM Prompts:**
   ```bash
   uv run pytest tests/test_agent.py::test_no_truth_leak -q
   ```
   *Proof:* The agent prompt contains only candidate transaction fields (amount, date, UTR, narration). It never sees truth labels, expected cohorts, or target group IDs.

2. **Negative Controls Falsifiability:**
   ```bash
   uv run pytest tests/test_eval.py::test_negative_controls -q
   ```
   *Proof:* All 6 negative controls (`shuffled_truth`, `null_agent`, `random_matcher`, `poisoned_prompt`, `inverted_rule`, `disabled_dedup`) fail the threshold gate as expected, proving the metrics are not hardcoded or immune to degradation.

3. **Pure Core Zero-I/O Isolation:**
   ```bash
   uv run lint-imports
   ```
   *Proof:* `engine/core/**` contains no network, filesystem, clock, or environment dependencies.

4. **Link-Level Evaluation vs Candidate Space:**
   ```bash
   uv run pytest tests/test_grader.py::test_link_confusion_hand_computed -q
   ```
   *Proof:* Accuracy is measured at the binary edge level across all candidate pairs $|C|$, not inflated by counting entire groups as single binary successes.

5. **Closed-Loop Reversibility & Convergence:**
   ```bash
   uv run pytest tests/test_live_wiring.py::test_second_pass_convergence_live -q
   ```
   *Proof:* Executing closures leaves open exceptions intact, and running a second reconciliation pass produces 0 new closures.

---

## 2. Five Real World Architectural Defenses

| Failure Mode | Naive Implementation | Our Architectural Defense |
|---|---|---|
| **Hallucinated Matches** | LLM generates synthetic IDs | Guardrail enforces candidate-space membership check (Stage 3) |
| **Float Rounding Drift** | `0.1 + 0.2 = 0.30000000000000004` | Strict integer paise everywhere (`amount_paise: int`) |
| **Silent Exception Loss** | Unmatched rows dropped from report | `sum(resolved) + sum(unresolved) == rows_total` invariant enforced |
| **Overfitting Dev Seeds** | Tuning directly on evaluation set | 20 holdout seeds (101–120) strictly separated from dev seeds (1–10) |
| **Triage Mutating Audit** | User edits change historical numbers | Triage updates `exceptions` table only; `runs.report` is immutable |

---

## 3. Quickstart Reproduction (Under 2 Minutes)

```bash
# 1. Run all checks
bash scripts/checks/all.sh

# 2. Run holdout seed evaluation sweep
uv run python -m engine.eval.sweep --seeds 101-120

# 3. Verify negative controls
uv run python -m engine.tools.crosscheck --controls
```
