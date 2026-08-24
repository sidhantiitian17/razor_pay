# razor_pay — AI Finance Controller

A 3-way settlement reconciliation engine (bank ↔ gateway payout ↔ ledger) with a
bounded LLM-agent matching path, and an institutional web dashboard for the result.
Money is integer paise everywhere except the display layer. Every reported metric
carries its numerator, denominator, seed, and seed-set — see
[`docs/FALSIFICATION.md`](docs/FALSIFICATION.md) for exactly what would prove this
project's claims wrong.

**Status:** in progress. See [`PROGRESS.md`](PROGRESS.md) for the authoritative
phase-by-phase status — do not infer completeness from this file; PROGRESS.md is
updated after every phase and is the source of truth.

## What works today

The engine and generator (through the deterministic matcher) run end to end:

```bash
uv sync
uv run razor-pay generate --n 100 --seed 42 --out data
uv run razor-pay run --mode rules_only --seeds 42 --n 100 --report-out reports/baseline.json
```

This writes synthetic bank/payout/ledger CSVs to `data/`, runs the rules-only
matcher, and writes a full `ReconciliationReport` (matching
[`contracts/report.schema.json`](contracts/report.schema.json)) to
`reports/baseline.json`. Open it and check `accuracy.match_rate.numerator` /
`.denominator` by hand against `data/` — that's the whole point of publishing both.

`--mode` also accepts `random` (chance-floor baseline, no agent). `agent_only` and
`rules_agent` are wired in the CLI's choices but the agent/guardrail path (P3) is
still being built — don't expect a populated result from them yet. `razor-pay
compare` is a stub.

## The dashboard

```bash
cd ui
bun install
bun run dev
```

The full app shell, run dashboard, exception workqueue, agent trace, live verify,
and eval lab are built (P7–P11) and render correctly against an empty Supabase
database — no run has been published there yet, so every page shows its honest
empty state rather than a fabricated number. The CLI above writes a local
`reports/baseline.json`; nothing currently publishes a run into Supabase's `runs`
table for the UI to pick up (that's P12, Live Wiring, not done yet).

## Repository layout

- `engine/` — the Python reconciliation engine (generator, matcher, agent, closer,
  reporter). See `PLAN.md` and `IMPLEMENTATION_PLAN.md` for the full design.
- `contracts/` — the frozen `report.schema.json` and the Supabase migration. Neither
  is ever hand-edited by the UI build; both are authored here and applied verbatim.
- `ui/` — the TanStack Start + Supabase dashboard, built via Lovable and reconciled
  into this repo (see `END_TO_END.md` §7 for that protocol).
- `tests_ui/` — Playwright specs for the UI's own exit gates (in progress).
- `docs/` — `FALSIFICATION.md` today; `ARCHITECTURE.md`, `VERIFICATION.md`,
  `ANTI_SLOP.md`, `EVALUATION.md` land with P13.

## Documentation

- [`PLAN.md`](PLAN.md) — original brief and design constraints.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — the full phase-by-phase build
  plan, every check, and every requirement atom (R1–R10).
- [`END_TO_END.md`](END_TO_END.md) — the orchestration protocol this repo was built
  under (git discipline, the Lovable MCP protocol, the review roster).
- [`PROGRESS.md`](PROGRESS.md) — live phase status, branch/commit/tag per phase.
- [`docs/FALSIFICATION.md`](docs/FALSIFICATION.md) — what would prove this project's
  claims wrong, stated in advance.
- [`CHANGELOG.md`](CHANGELOG.md) — dated log of notable changes.
