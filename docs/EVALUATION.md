# Evaluation Methodology & Benchmark Results

This document defines the evaluation framework, dataset partitions, baseline comparisons, and statistical metrics across the reconciliation pipeline.

---

## 1. Seed Protocol & Partitioning

To eliminate evaluation leakage and prevent data-snooping:

- **Development Seed Set (`1–10`):** Used strictly for hyperparameter tuning, prompt development, and guardrail threshold curve fitting.
- **Holdout Benchmark Set (`101–120`):** 20 unseen evaluation seeds never used for tuning.
- **Regression Snapshot (`42`):** Fixed dev seed used for byte-stable deterministic regression assertions.
- **Gating Metric:** System pass/fail is gated strictly on the **worst holdout seed minimum** ($\min_{s \in 101..120} \text{match\_rate}(s)$), not merely on the mean.

---

## 2. Four-Arm Ablation Architecture

The system evaluates four distinct execution modes on identical datasets:

1. **`rules_only` (Deterministic Baseline):**
   - Pure deterministic rule stack (Exact UTR, Narration regex recovery, Fee-aware pair matching, Duplicates).
   - Expected match rate: ~74–80%.
   - LLM cost: $0.00.

2. **`agent_only`:**
   - Multi-turn LLM agent matching all candidate pairs directly without pre-filtering rules.
   - Measures raw LLM matching capability and token efficiency.

3. **`rules_agent` (Hybrid Production System):**
   - Deterministic rule stack runs first; unmatched residuals are escalated to the bounded LLM loop.
   - **`agent_lift`:** Evaluated as $\text{Recall}_{\text{rules\_agent}} - \text{Recall}_{\text{rules\_only}}$.
   - **`precision_cost`:** Evaluated as $\text{Precision}_{\text{rules\_only}} - \text{Precision}_{\text{rules\_agent}}$.

4. **`random` (Null Control):**
   - Random edge selection across candidate space $|C|$. Serves as the lower-bound falsification control.

---

## 3. Link-Level Evaluation Formulation

Evaluation is computed at the binary edge level across all candidate pairs in $|C|$:

- $\text{Link}_{\text{Bank-Payout}}$: Binary classification for each $(b, p) \in C_{\text{BP}}$.
- $\text{Link}_{\text{Bank-Ledger}}$: Binary classification for each $(b, l) \in C_{\text{BL}}$.
- $\text{Link}_{\text{Payout-Ledger}}$: Binary classification for each $(p, l) \in C_{\text{PL}}$.

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad \text{F1} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

---

## 4. Negative Controls Suite

CI executes all 6 falsification controls to verify metric sensitivity:

| Control | Description | Expected Verdict |
|---|---|---|
| `shuffled_truth` | Truth labels randomly permuted across entities | Precision drops to chance |
| `null_agent` | Agent returns empty match list | Fails agent_only threshold |
| `random_matcher` | Predicts random edges | Massive false positive surge |
| `poisoned_prompt` | Adversarial injection attempts to force matches | Guardrail rejects hallucinated IDs |
| `inverted_rule` | Inverts matching logic | Clean recall collapses to 0.0 |
| `disabled_dedup` | Removes duplicate suppression | Cardinality invariant fails |
