# Settlement Sentinel — AI Finance Controller

An institutional 3-way settlement reconciliation engine (**Bank Statement ↔ Gateway Payout ↔ General Ledger**) with deterministic rule stacks, a bounded LLM agent for the residual, audit-grade reversible closures, and a real-time operator console — built so every number it shows is computed from fetched data, never invented.

Money is strictly integer paise everywhere except the display layer. Every reported metric carries its explicit numerator, denominator, seed, and seed-set — no bare percentages.

---

## 1. The problem

Every payment company runs the same reconciliation loop, usually by hand: three independent records of the same money — what the **bank** says arrived, what the **payment gateway** says it paid out, and what the **general ledger** says was booked — have to agree, row for row, before finance can close the books. When they don't agree, someone has to figure out *why*: a delayed settlement, a duplicate, a fee mismatch, a timing window, a genuinely lost transaction.

Done manually, this is slow, error-prone, and gets worse as volume grows. Done with an LLM alone, it's fast but unauditable and prone to confidently inventing matches that aren't real. Settlement Sentinel is built to avoid both failure modes: **deterministic rules resolve the clean majority, a tightly bounded agent only touches the genuinely ambiguous residual, and everything either system produces is independently re-verifiable from the underlying rows.**

## 2. How it solves it

```
 Bank statement          Gateway payout           General ledger
      │                        │                        │
      └────────────────────────┼────────────────────────┘
                                ▼
                 ┌───────────────────────────────┐
                 │ 1. Candidate blocker            │  recall 1.0 over the
                 │    (|C| < n²/4, never exhaustive)│  candidate space — nothing
                 └───────────────┬───────────────┘  eligible is pruned early
                                 ▼
                 ┌───────────────────────────────┐
                 │ 2. Deterministic rule stack     │  exact / fuzzy / pair
                 │   (no LLM, 70.2% match rate)    │  matching, zero cost
                 └───────┬───────────────┬─────────┘
                         │               │
                  resolved matches   residual (unmatched)
                         │               ▼
                         │   ┌───────────────────────────┐
                         │   │ 3. Bounded LLM agent        │  confidence ≥ 0.70,
                         │   │    multi-turn, schema-locked│  ≥2-field corroboration,
                         │   └───────────────┬─────────────┘  can never override a
                         │                   ▼                 deterministic match
                         │   ┌───────────────────────────┐
                         │   │ 4. Deterministic guardrail  │  5-stage accept/reject,
                         │   │    (rejects hallucinations) │  never trusts the LLM alone
                         │   └─────┬───────────────┬───────┘
                         │     accepted          rejected
                         │         │                 ▼
                         └─────────┤        ┌─────────────────┐
                                   ▼         │ Exception queue  │  9 target buckets,
                       ┌─────────────────┐   │ (evidence-first) │  reversible triage
                       │ Idempotent close │   └─────────────────┘
                       │ balanced journal │
                       └────────┬────────┘
                                ▼
                  ┌─────────────────────────────┐
                  │ Grader + Verify page          │  every check is *computed*
                  │ (negative controls, falsifiers)│  live from fetched rows —
                  └─────────────────────────────┘  a check that can't fail
                                                     proves nothing, so each one
                                                     ships with a poisoned-input
                                                     test proving it can
```

**The core design decision:** the LLM agent is never trusted by default. It proposes; a separate, deterministic guardrail (confidence threshold, multi-field corroboration, anti-hallucination ID checks, bounded delta tolerance, and "can never override a rule-based match") decides. Anything the guardrail rejects becomes an evidence-first exception for a human operator — never a silent write. Every closure records a before/after snapshot so it can be exactly reversed. And the product refuses to claim confidence it hasn't earned: the **Eval Lab** measures match rate against 20 *holdout* seeds the system has never tuned against, and the **Verify** page recomputes every anti-slop check live from the database rather than rendering a canned "passed" badge — each check ships with a poisoned-fixture test proving it can genuinely fail, not just genuinely pass.

Full write-up, principles, and the 12-table schema: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 3. What's in the console

The operator console (`ui/`) is a TanStack Start + Supabase app, gated behind real Supabase Auth (row-level security is the actual boundary — an anonymous visitor has no SELECT grant on any reconciliation table, not just a hidden UI).

| Route | What it shows |
|---|---|
| **Runs** | Every reconciliation run, match rate and unresolved count side by side, newest first. |
| **Run Dashboard** | Headline KPIs with numerator/denominator, dual confusion matrices, 4-arm ablation panel, resolved-tag vocabularies kept separate from unresolved buckets. |
| **Exceptions** | 9-bucket virtualized triage queue — each row shows its source diff and audit evidence string, closures are reversible. |
| **Agent Trace** | Every LLM call in order: input, tool use, guardrail verdict — nothing the agent decided is a black box. |
| **Eval Lab** | Dev/holdout/regression seed sweeps kept apart; the reported gate value is the *worst* holdout seed, never the best demo seed. |
| **Verify** | Anti-slop checks, negative controls and falsifiers, computed live and printing the evidence behind each verdict. |

Live: **https://razorpay-settlement-sentinel.lovable.app**

## 4. Setup

Two independent halves — the reconciliation engine (Python) and the operator console (TypeScript). You don't need both to explore either one: the engine runs fully offline against a local SQLite file, and the console can point at the shared Supabase project below.

### 4.1 Prerequisites
- Python ≥ 3.11 (repo pins 3.13) with [`uv`](https://docs.astral.sh/uv/)
- Node ≥ 20 with [`bun`](https://bun.sh)
- A Supabase project (only needed if you want the console reading live data — use the shared dev project's public anon key, or your own)

### 4.2 Engine — generate a dataset and run reconciliation
```bash
git clone https://github.com/sidhantiitian17/razor_pay.git
cd razor_pay
uv sync --all-extras

# synthetic 3-way dataset (bank / payout / ledger)
uv run python -m engine.cli generate --n 100 --seed 42 --out data

# run the pipeline (rules + bounded agent) and publish the report
uv run python -m engine.cli run --mode rules_agent --seeds 42 --n 100 \
  --report-out reports/run_42.json --publish

# add --fast for an interactive/demo run: skips the ~4x per-run ablation
# recompute (the report then carries "ablation": null — skipped, never faked)
uv run python -m engine.cli run --mode rules_agent --seeds 42 --n 100 --fast
```

By default the bounded agent runs against the offline `HeuristicLLMClient` —
deterministic, network-free, and what CI uses. To measure against a real
model instead, set `ANTHROPIC_API_KEY` before the `run` command; the engine
picks it up automatically and records which backend actually ran in
`config.agent_backend` on the published report, so a reviewer never has to
guess.

### 4.3 Evaluate against holdout seeds
```bash
# 20 seeds the system was never tuned against
uv run python -m engine.eval.sweep --seeds 101-120

# 4-arm ablation: rules_only / agent_only / rules_agent / random
uv run python -m engine.eval.ablation --seeds 101-120
```

### 4.4 Verify the published data (anti-slop check)
```bash
# diffs the published DB rows against report.json — zero UI fabrication allowed
uv run python -m engine.tools.crosscheck --run <run_id>
uv run python -m engine.tools.crosscheck --controls   # all 6 negative controls
```

### 4.5 Operator console
```bash
cd ui
cp .env.example .env   # fill in your Supabase project URL + anon key
bun install
bun run dev
```
Sign up on `/auth` (Supabase email/password) — new accounts need an operator role granted before the reconciliation tables become readable (RLS-enforced, not a UI gate); ask an existing admin or grant it directly against `public.user_roles`.

### 4.6 Full regression net
```bash
bash scripts/checks/all.sh   # every phase's check script, P0 through P13
```

## 5. Results (holdout seeds 101–120)

| Metric | Value |
|---|---|
| Candidate blocker recall | 1.0000 (100%, over a candidate space $\lvert C\rvert < n^2/4$) |
| Rules-only match rate | 70.2% mean, stdev 0.0151 (zero LLM cost) |
| Rules + bounded agent match rate | 70.2% mean — **no lift on this exact metric today** (see note below) |
| Agent-only match rate | 23.2% mean, 99.6% precision (agent resolves the full journal, not just the bank↔payout pair) |
| Bank–payout link recall, rules-only → rules+agent | 75.7% → 78.1% (genuine `+2.4pt` lift on the link-level metric) |
| Bank–payout link precision, rules-only → rules+agent | 100.0% → 100.0% (the agent adds no false-positive links) |
| Payout–ledger link recall, rules-only → rules+agent | 74.4% → 76.3% (`+1.9pt` — the agent's ledger-side proposals) |
| `agent_lift` / `precision_cost` on `match_rate` | 0.0 / 0.0 (reported as measured; neither is smoothed) |
| Negative controls verified falsifiable | 6 / 6 |
| Worst-case holdout minimum (gate value) | 67.00% (seed 114) |

Every figure above is **reproducible byte-for-byte**: `uv run python -m engine.eval.ablation --seeds 101-120` gives the same numbers on every process, with or without `PYTHONHASHSEED` set (the agent's candidate iteration is sorted, so nothing depends on Python's per-process hash randomisation).

**Why `match_rate` and bank–payout recall disagree:** `match_rate` requires an *exact* 3-way match — bank, payout, **and** ledger lines all correct against the recorded truth group. The bounded agent now proposes the ledger side too: on any residual whose payout has a clean, balanced journal reachable in the candidate space it fetches that journal (every entry keyed on `reference == payout_id`, signed amounts netting to zero) and includes those `ledger_ids` in `propose_match`. That is what lifts the **agent-only** arm to 23.2% match rate at 99.6% precision — the agent genuinely does 3-way work, not just bank↔payout linking.

The **headline `rules_agent` match rate still shows no lift**, for a reason that is now a property of the benchmark rather than a gap in the agent: after the deterministic rule stack runs, the residuals it leaves are — by cohort design — the genuinely *unresolvable* cases (duplicate payout, excess drift, fee mismatch), not clean 3-way groups waiting to be recovered. Moving the headline number would require adding an "agent-resolvable 3-way" cohort to the generator, which would be benchmark-gaming; we would rather report the flat number honestly. All of this is measured and reproducible (`uv run python -m engine.eval.sweep --seeds 101-120`, `uv run python -m engine.eval.ablation --seeds 101-120`), not an estimate.

Every number above is produced by the code as shipped — including the four ablation arms, which are *actually rerun* per seed rather than partially hardcoded, and `agent_lift`, which is reported at its true value (0.0 here) rather than clamped up to a floor (see [`CHANGELOG.md`](CHANGELOG.md) for the remediations this replaced). Which LLM backend produced the `agent_only`/`rules_agent` numbers in any given report is always recorded verbatim in `config.agent_backend` (`"live"`, `"heuristic"`, or `"none"`) — set `ANTHROPIC_API_KEY` to measure against a real model instead of the offline simulator.

## 6. Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — topology, pure-core isolation, guardrail design, 12-table schema, scalability roadmap.
- [`VERIFICATION.md`](VERIFICATION.md) — step-by-step reproduction guide for reviewers and CI.
- [`ANTI_SLOP.md`](ANTI_SLOP.md) — 10-minute reviewer's guide to falsifiability and zero truth-leak.
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — evaluation methodology and the 4-arm ablation design.
- [`docs/FALSIFICATION.md`](docs/FALSIFICATION.md) — six refutation conditions, stated in advance.
- [`PROGRESS.md`](PROGRESS.md) · [`CHANGELOG.md`](CHANGELOG.md) — phase ledger and dated changelog.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — master design spec and requirement atoms (R1–R10).

## 7. License

MIT — see [`LICENSE`](LICENSE).

## 8. Tech stack

**Engine:** Python 3.13, Pydantic v2, pure-core matching (zero I/O, enforced by `import-linter`), SQLite / Supabase Postgres storage adapters, `uv` for dependency management.
**Console:** TanStack Start + React 19, Tailwind v4 + shadcn/ui, Supabase Auth + Postgres (RLS as the real security boundary), GSAP/Lenis for scroll interaction, Framer Motion for reduced-motion-aware transitions, Recharts, Playwright for UI verification.
**CI:** ruff, mypy --strict, import-linter, pytest with coverage, pip-audit, gitleaks, and a frozen-schema diff gate that fails the build if `report.d.ts` drifts from `contracts/report.schema.json`.
