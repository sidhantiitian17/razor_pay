# Changelog

All notable changes to this project are recorded here, one entry per merged phase.

## [P3] — Agent Loop, Guardrail, Replay — 2026-08-25

### Added
- `engine/ports/llm.py` — protocol definitions for LLM client, structured request/response, token and dollar cost accounting (`UsageStats`).
- `engine/ports/store.py`, `clock.py` — storage and UTC clock ports.
- `engine/adapters/llm_replay.py` — deterministic cassette recorder and replay adapter with `BlockingTransportAsserter` guaranteeing zero network calls and stripped auth secrets (check 3.6, 3.10, ADR-001).
- `engine/core/guardrail.py` — deterministic guardrail validator evaluating confidence, multi-field requirements, hallucinated IDs, amount delta, and timing skew (check 3.7, R8, D15).
- `engine/app/agent.py` — bounded multi-turn tool loop with `AGENT_TOOLS_SCHEMA` (`fetch_candidates`, `inspect_record`, `propose_match`), typed errors (`FreeTextResponseError`, `TurnLimitExceededError`), prompt injection defense, and truth isolation I12 (checks 3.1–3.5, 3.9, 3.11–3.13).
- `engine/eval/threshold.py` — threshold sweeper and PR curve evaluator over dev seeds saving `reports/threshold_sweep.json` (check 3.8, D15, §4.4).
- `scripts/checks/P3.sh` — automated verification runner for checks 3.1 through 3.13.

### Verified
- **Checks:** 3.1–3.13 PASS (13/13). `uv run pytest tests/ -q`: 107/107 passed (80% overall, 98% on guardrail, 91% on agent). `ruff check` / `ruff format --check`: clean. `mypy --strict engine`: clean. `lint-imports`: Core purity kept. `gitleaks detect --no-git`: 0 findings.
- **Exit gate:** 3.4 (truth isolation I12), 3.6 (deterministic replay without network calls), and 3.11 (multi-turn loop) verified.

## [P2] — Blocker, Deterministic Matcher, Baseline — 2026-08-25

### Added
- `engine/core/matching/blocker.py` — candidate space blocker `C` construction and `evaluate_blocker_recall` achieving 1.0 recall across all seeds 1..20 while capping space size to `< n^2 / 4` (check 2.1, 2.2, §4.2).
- `engine/core/matching/attribute.py` — 3-way outlier attribution logic for triads (bank, payout, ledger) mapping breaks to `AMOUNT_MISMATCH`, `FEE_MISMATCH`, and `PARTIAL_GROUP` (check 2.8, §3.4).
- `engine/core/matching/rules.py` — deterministic rule stack for exact UTR matches, duplicate detection, narration UTR recovery, refund reversals, and residual exceptions (checks 2.3–2.7).
- `engine/core/metrics.py` — reconciliation metrics engine calculating link confusion matrices, exact match rate, resolved/unresolved rates (I9, I10, I11, D5).
- `engine/app/reporter.py` — report generator serializing to `contracts/report.schema.json` format.
- `engine/cli.py` — implemented `run --mode rules_only --seeds 101-120` command publishing to `reports/baseline.json` (D7).
- `scripts/checks/P2.sh` — automated verification runner for checks 2.1 through 2.10.
- `reports/baseline.json` — baseline benchmark for rules-only arm on holdout seeds 101–120.

### Verified
- **Checks:** 2.1–2.10 PASS (10/10). `uv run pytest tests/ -q`: 90/90 passed (84% coverage). `ruff check` / `ruff format --check`: clean. `mypy --strict engine`: clean. `lint-imports`: Core purity kept. `gitleaks detect --no-git`: 0 findings.
- **Exit gate:** Blocker recall is 1.0 (nothing dropped downstream) and baseline report published to `reports/baseline.json`.

## [P1] — Generator, Journals, Ground Truth — 2026-08-24

### Added
- `engine/core/generator/allocate.py` — largest-remainder cohort allocator guaranteeing sum(counts) == n for all n >= 50 (D11).
- `engine/core/generator/journals.py` — balanced journal construction (`make_settlement_journal`, `make_refund_reversal_journal`) satisfying zero-sum invariant I3.
- `engine/core/generator/cohorts.py` — full suite of 13 registered cohort injectors and `COHORT_TERMINAL_MAP` covering all 5 resolved tags and 8 generated exception buckets.
- `engine/core/generator/build.py` — `generate_dataset` orchestration, deterministic RNG with seed stability, partition verification (I5), cardinality verification (I8), truth links derivation (§4.1), and CSV/JSON export (`write_csvs`).
- `engine/cli.py` — implemented `generate --n <n> --seed <seed> --out <dir>` sub-command.
- `scripts/checks/P1.sh` — automated verification runner for checks 1.1 to 1.11.
- `tests/test_allocate.py`, `tests/test_cohorts.py`, `tests/test_generator.py` — 15 unit tests covering checks 1.1–1.11.

### Verified
- **Checks:** 1.1–1.11 PASS (11/11). `uv run pytest tests/ -q`: 77/77 passed (85% coverage). `ruff check` / `ruff format --check`: clean. `mypy --strict engine`: clean. `lint-imports`: 1 contract kept. `gitleaks detect --no-git`: 0 findings.
- **Exit gate:** Truth partition (I5) and 1:1 cohort-to-terminal state mapping (I6) verified.

## [P0] — Contracts, Data Model, Decisions — 2026-08-24

### Added
- `contracts/report.schema.json` — frozen report contract (draft 2020-12 JSON Schema)
- `contracts/migrations/001_init.sql` — Supabase schema + RLS for all 13 tables
- `ui/src/types/report.d.ts` — generated TypeScript types from the frozen schema
- `engine/core/models.py`, `money.py`, `timewin.py` — frozen Pydantic model set, integer-paise money, tz-aware UTC time windows
- `docs/adr/ADR-001..006.md` — cassette policy, currency scope, ledger sign convention, bar negotiability, seed protocol, grading unit
- `scripts/checks/P0.sh`, `scripts/checks/all.sh` — phase check runner + regression net
- `.github/workflows/ci.yml` — CI skeleton
- `.gitignore`, `.gitattributes`, `.gitleaks.toml` — repo hygiene, LF enforcement, secret-scan scope
- `pyproject.toml` — dependency set, mypy/ruff/import-linter/pytest config

### Fixed
- import-linter's "Grader isolation" contract referenced `engine.core.grader`, a module that doesn't exist until P5 — import-linter hard-errors on a `source_modules` entry that can't resolve. Deferred the contract (commented, with the exact block to restore) to the P5 commit that creates `grader.py`.
- Windows console (cp1252) crashed on import-linter's unicode/box-drawing status output, masking the real error above with a `UnicodeEncodeError` traceback. `scripts/checks/P0.sh` now exports `PYTHONUTF8=1`.
- `types_generate` (check 0.5) was piping `json-schema-to-typescript` to `/dev/null` — the actual P0 deliverable (`ui/src/types/report.d.ts`) was never written. Now generates and verifies the real file; full `tsc --noEmit` against the `ui/` project moves to check 7.1 once P7 scaffolds that project.
- `gitleaks detect --no-git` was scanning `.venv/` (204 false positives from vendored license data) since it ignores `.gitignore` in that mode. Added `.gitleaks.toml` allowlisting vendored/generated paths.

### Removed
- `src/razor_pay/__init__.py` — orphaned scaffold from before the `engine/` layout (IMPLEMENTATION_PLAN.md §6) was adopted; unreferenced by `pyproject.toml`, never committed.

### Review findings (database-reviewer + security-reviewer, §6.2) — fixed before merge
- **CRITICAL:** `CREATE POLICY IF NOT EXISTS` is not valid PostgreSQL syntax (unlike `CREATE TABLE`/`CREATE INDEX`) — the migration would abort with a syntax error on first apply. Rewritten as `DROP POLICY IF EXISTS <name> ON <table>; CREATE POLICY <name> ...` pairs for all 33 policies — genuinely idempotent, actually applies.
- **HIGH:** `closures` (write-back before/after state) was exposed to `anon`/`authenticated` SELECT — not in the §5.2 role table, which lists it as service_role-only like `run_requests`. Removed both policies.
- **HIGH/MEDIUM:** `auth_update_exceptions`'s row-level policy alone let `authenticated` overwrite any column on an exception, not just the triage fields (RLS is row-scoped, not column-scoped). Added `REVOKE UPDATE ON exceptions FROM authenticated` + `GRANT UPDATE (status, assignee, resolution_note) ON exceptions TO authenticated` so only triage columns are writable.
- **MEDIUM:** `run_requests.result_run_id` (FK to `runs`) had no index; added `idx_run_requests_result_run`.
- `tests/test_rls.py` did pure substring matching with no live SQL execution, so none of the above would have been caught by CI. Added 4 regression-guard tests: no invalid `IF NOT EXISTS` policy syntax, every `CREATE POLICY` has a matching `DROP POLICY IF EXISTS`, `closures` has no anon/authenticated SELECT, `exceptions` UPDATE is column-restricted. Real SQL execution against a live Postgres is still deferred to P6 (Supabase not yet provisioned) — recorded here per §13.6.
- `match_groups.confidence` and `agent_calls.cost_usd` as `DOUBLE PRECISION` reviewed and kept as-is: these are a score and a USD reporting estimate, not ledger money in paise — I1 ("no float in any money path") applies to the `*_paise` columns, all of which are `BIGINT`.

### Code quality (surfaced by installing the §9.1 pre-commit hook — ruff had never actually been run before)
- Consolidated three duplicated inline `_validate_paise` field validators (`BankTxn`, `GatewayPayout`, `LedgerEntry`) into one shared `_check_paise` helper delegating to `engine.core.money.validate_paise` — the import was staged unused, a DRY smell pointing at real duplication.
- Fixed the bridge: Pydantic v2 field validators only convert `ValueError`/`AssertionError` into `ValidationError`; `validate_paise` raises `TypeError` by contract (asserted directly in `tests/test_money.py`), so it now gets re-raised as `ValueError` inside the model validator instead of propagating uncaught and failing model construction with a raw `TypeError`.
- `tests/test_money.py::test_no_float_literals` had a dead, nonsensical line (`inspect.getsource(validate_paise.__module__ and __import__(...))`, result never used) left over ahead of the real AST-based check — removed.
- 4 enums (`GroupKind`, `ResolvedTag`, `ExceptionBucket`, `CohortName`) upgraded from `(str, enum.Enum)` to `enum.StrEnum` (ruff UP042, Python 3.11+).
- Added `per-file-ignores` for `tests/*` on `D101/D102/D103` (missing docstrings) — test method names are the documentation per this project's own testing convention; a docstring restating the name on every one of 60+ test methods is noise.
- `date`/`datetime` in `engine/core/models.py` kept as real (non-`TYPE_CHECKING`) imports with an explicit `noqa: TC003` + comment: Pydantic resolves string annotations at runtime via `typing.get_type_hints`, so moving them under `TYPE_CHECKING` would break model construction — a case where the lint suggestion is wrong for this framework.
- Minor: `ClassVar` annotation on a test's list constant (RUF012).

**Checks:** 0.1–0.13 PASS (13/13). `uv run pytest tests/ -q`: 62/62 passed. `ruff check` / `ruff format --check`: clean. `gitleaks detect --no-git`: 0 findings. **Exit gate:** schema frozen — any later change requires a `schema_version` bump plus a regenerated `report.d.ts` in the same commit.
