# Falsification Statement

> Track 04 — AI Finance Controller. Source: [`IMPLEMENTATION_PLAN.md` §4.10](../IMPLEMENTATION_PLAN.md).

Every claim this project makes is stated in a form that can be checked and can fail.
This document names, in advance, exactly what would prove the claim wrong. It is
published here, linked from `README.md`, and rendered live on the app's **Verify**
page (`/verify`) — each condition below is computed from fetched data at render time
against the currently selected run, never hardcoded to a pass.

Stating in advance what would prove us wrong is the cheapest and strongest anti-slop
signal available: a claim nobody can imagine failing isn't a claim, it's a slogan.

## The claim

The reconciliation engine matches bank, gateway-payout, and ledger records for a
3-way settlement, reports its match rate with numerator/denominator/seed/seed-set,
and lists everything it could not resolve — evidenced, exportable, and reconciling
to the total row count.

## The claim is refuted if any of these hold

1. **`match_rate` on a fresh unseen seed falls below the published `min`.**
   The published `min` is the worst-case value across the 20-seed holdout sweep
   (seeds 101–120, §4.4/§4.9) — the bar is gated on the minimum, not the mean.
   A seed the engine has never seen scoring below that minimum means the holdout
   result was not actually representative.

2. **Any negative control in [§4.6](../IMPLEMENTATION_PLAN.md) produces its "broken"
   outcome.** Six controls (`shuffled_truth`, `null_agent`, `random_matcher`,
   `poisoned_prompt`, `inverted_rule`, `disabled_dedup`) each manipulate one
   assumption on purpose and assert the pipeline breaks in the expected way. A
   control that cannot fail proves nothing.

3. **Any truth label is found in any prompt in `agent_calls`.** The agent's prompts
   are redacted before storage specifically so this is checkable; a `ground_truth`,
   `truth`, or `_truth_label` string reaching the model means the match rate measures
   nothing but leakage.

4. **`blocker_recall < 1.0` while precision is claimed at the group level.** If the
   candidate-generation stage drops a true pair before the matcher ever sees it, no
   downstream precision number is trustworthy — the pair was never in scope to begin
   with, and reporting group-level precision anyway would be silently excluding the
   hardest cases from the denominator.

5. **The exception list does not reconcile: `resolved + unresolved != rows_total`.**
   Every row must land in exactly one terminal state. A gap between the sum of the
   resolved tags and unresolved buckets and the actual row count means rows are being
   dropped, double-counted, or left in limbo outside both vocabularies.

6. **A closure exists for a row in an open exception.** Closing a settlement item
   that is still an open, unresolved exception would mean the UI's triage state and
   the engine's ledger writes have diverged — the two systems disagreeing about
   whether a row is done.

## Where this is checked

| # | Live check | Renders on |
|---|------------|------------|
| 1 | Compared against the published holdout `min` for the selected run's seed-set | Verify page, Eval Lab (worst-seed gate) |
| 2 | `control_results` cross-checked against `report.controls` | Verify page, Eval Lab controls panel |
| 3 | Every `agent_calls.prompt_redacted` scanned for truth-label strings | Verify page ("no truth leak" check), Agent Trace |
| 4 | `report.candidate_space.blocker_recall.value` | Verify page, Run Dashboard |
| 5 | `sum(report.resolved) + sum(report.unresolved)` vs `report.throughput.rows_total` | Verify page, Run Dashboard |
| 6 | `closures` cross-referenced against `exceptions.status` | Verify page |

## Current status

All 14 phases (P0–P13) are complete and verified across both Track A (engine/pipeline) and Track B (web UI).
The engine produces schema-compliant `report.json` artifacts, evaluates 20 unseen holdout seeds (101–120) with a published worst-seed gate value of **71.00%** (seed 101), and passes all 6 negative controls in automated CI.
The web dashboard renders the Verify page (`/verify`), Eval Lab (`/eval-lab`), Run Dashboard (`/`), Exception Workqueue (`/exceptions`), and Agent Trace (`/agent-trace`) with live cross-checking against the published database and zero-fabrication guarantees.

