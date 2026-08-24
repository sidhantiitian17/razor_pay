# Track 04 — AI Finance Controller: Implementation Plan

**Loop:** 3-way payment reconciliation (bank statement ↔ Razorpay payout ↔ internal ledger)
**Batch size:** 60–100 synthetic records per source
**Success bar:** measured match rate + typed exception list + reproducible eval + zero cherry-picking

---

## 1. Executive Summary

Build a hybrid deterministic + LLM agent that closes the payment reconciliation loop end-to-end on a labeled synthetic batch, reports honest match rate + precision/recall, and produces a machine-verifiable exception ledger.

**Non-goals:** production DB, web UI, multi-tenant auth, streaming ingest. Local CLI only. This is a demonstrator, not a service.

---

## 2. Problem Statement & Why This Loop

Finance ops teams manually match bank credits to gateway payouts to ledger entries. Errors: paise drift from FX/rounding, timing skew across cutoffs, missing UTR references, duplicate payouts on retry, refund/reversal pairs, orphan credits.

**Why 3-way recon (not forecaster/tax-matcher/QA):**

| Criterion | Recon | Forecaster | Tax-matcher | Settlement QA |
|-----------|-------|------------|-------------|---------------|
| Objective match rate metric | Yes | No (predictive, no truth) | Yes | No (subjective) |
| Rich exception taxonomy | Yes | Partial | Partial | No |
| Throughput demo | Yes | Partial | Yes | No (LLM-bound) |
| Fits `razor_pay` domain | Yes | Partial | Partial | Yes |
| Defensible against "AI slop" claim | Yes | No | Yes | No |

Recon wins on all axes that map to the stated bar.

---

## 3. Architecture

```
                  +-----------------------------------------+
                  |           CLI (src/cli.py)              |
                  |  run --n 60 --seed 42 --agent haiku     |
                  +---------------+-------------------------+
                                  |
             +--------------------+--------------------+
             v                    v                    v
      +--------------+     +--------------+     +--------------+
      |  Generator   |     |   Pipeline   |     |   Reporter   |
      | (Phase 1)    |     | (Phase 2-4)  |     | (Phase 4)    |
      +------+-------+     +------+-------+     +------+-------+
             |                    |                    |
             v                    |                    v
      +--------------+            |             +--------------+
      | data/*.csv   |            |             | reports/*    |
      | + ground_    |            |             | report.json  |
      |   truth.csv  |            |             | report.md    |
      +--------------+            |             +--------------+
                                  |
             +--------------------+--------------------+
             v                    v                    v
      +--------------+     +--------------+     +--------------+
      | Deterministic|---->|  LLM Agent   |---->|  Exception   |
      |   Matcher    |     | (Anthropic   |     |  Classifier  |
      | (rules)      |     |  Haiku 4.5)  |     |              |
      +--------------+     +------+-------+     +--------------+
                                  |
                                  v
                           +--------------+
                           |  Guardrail   |
                           |  (confidence |
                           |   + citation)|
                           +--------------+
```

**Data flow:**
1. Generator emits 3 CSVs + labeled ground truth
2. Deterministic matcher matches exact tuples, produces residual set
3. Agent processes only residuals with tool-forced structured output
4. Guardrail rejects low-confidence or uncited proposals
5. Classifier buckets remaining unmatched into 7 typed causes
6. Reporter joins pipeline output vs ground truth, emits metrics + exception ledger

**Boundaries (verifiable, testable):**
- Generator: pure function of `(n, seed, defect_mix)`, deterministic output
- Matcher: pure function of `(sources) -> (matched, residual)`
- Agent: side-effectful (API call), wrapped in cassette for reproducibility
- Reporter: pure function of `(pipeline_output, ground_truth) -> metrics`

Each boundary crossable by a unit test in isolation.

---

## 4. Tech Stack & Justification

| Layer | Choice | Justification | Rejected alternative |
|-------|--------|---------------|---------------------|
| Language | Python 3.11 | Ecosystem for finance/data; pydantic + pandas mature | Node/TS (weaker data libs); Go (no LLM ergonomics) |
| Package mgr | `uv` | 10-100x faster than pip; lockfile deterministic | pip (slow); poetry (heavier) |
| Schema | Pydantic v2 | Runtime validation at boundaries, JSON schema export for LLM tool defs | dataclasses (no validation); attrs (no LLM integration) |
| Data | pandas | CSV round-trip, groupby matching primitives | polars (fine, pandas familiarity higher for reviewers); plain csv (no join ergonomics) |
| LLM SDK | anthropic (official) | Prompt caching, tool use, structured output | openai (out of scope for spec); langchain (unnecessary abstraction) |
| Model | Haiku 4.5 | 3x cheaper than Sonnet at ~90% capability for classification; throughput fits >=50 rows demo | Sonnet (over-spec for row-level match); Opus (cost blowout, no reasoning gain here) |
| Testing | pytest + pytest-cov | Standard; snapshot support via syrupy | unittest (verbose); nose (unmaintained) |
| Recording | VCR.py (cassettes) | Deterministic replay of API responses in CI | mock (loses fidelity); live-call-only (nondeterministic + costly) |
| Config | pydantic-settings | Env-var driven, typed | argparse-only (no env fallback); hydra (heavy) |
| Logging | structlog | Structured JSON logs, greppable | stdlib logging (unstructured); loguru (opinionated formatting) |
| Metrics | prometheus_client (in-proc) | Standard exposition format; scrapeable later | custom counters (reinventing) |
| CI | GitHub Actions | Free tier, standard | none (kills verifiability claim) |
| Formatter | ruff | Format + lint in one, fast | black + flake8 (two tools) |
| Type check | mypy --strict | Catches schema drift before runtime | pyright (fine alternative; mypy chosen for ecosystem) |

**Every dep pinned in `pyproject.toml` with upper bound.** Lockfile committed. Reason: reproducibility is the point of a demonstrator.

---

## 5. Module Design

Small files, single responsibility, no cross-imports except through explicit interfaces.

```
D:\razor_pay\
- pyproject.toml
- uv.lock
- .env.example              # ANTHROPIC_API_KEY=...
- .gitignore                # .env, __pycache__, .venv, reports/*.json (keep .md)
- README.md                 # 5-min quickstart
- PLAN.md                   # this file
- ARCHITECTURE.md           # generated diagrams + rationale
- VERIFICATION.md           # how to verify each phase (see Section 14)
- ANTI_SLOP.md              # beginner verification guide (see Section 21)
- src/
  - __init__.py
  - config.py               # pydantic-settings, env vars
  - schema.py               # BankTxn, GatewayPayout, LedgerEntry, MatchTriple, Exception
  - generator.py            # synthetic data + ground truth
  - defects.py              # defect injection strategies (isolated for test)
  - match_rules.py          # deterministic matcher
  - agent.py                # LLM loop, tool defs
  - guardrail.py            # confidence + citation gate
  - exceptions.py           # 7-way classifier
  - report.py               # metrics + markdown/json writer
  - observability.py        # structlog + prometheus setup
  - cli.py                  # entrypoint
- data/                     # gitignored except .gitkeep
- reports/                  # gitignored except sample_report.md
- cassettes/                # VCR recordings, committed
- tests/
  - conftest.py             # fixtures, seed control
  - test_generator.py       # deterministic given seed
  - test_defects.py         # each defect type produces expected shape
  - test_match_rules.py     # matcher precision on synthetic
  - test_agent.py           # cassette-replay, tool call shape
  - test_guardrail.py       # rejects low-confidence, missing citation
  - test_exceptions.py      # classifier bucket correctness
  - test_report.py          # metrics math correctness
  - test_e2e.py             # full pipeline vs ground truth, assert bar
  - test_regression.py      # snapshot report against golden
- .github/workflows/
  - ci.yml                  # test, lint, typecheck, coverage
  - eval.yml                # runs e2e + posts report as PR artifact
```

**Rule:** any file >300 lines gets split. Any function >40 lines gets refactored. Any nesting >3 gets flattened via early returns.

---

## 6. Data Model

All models Pydantic v2 with `model_config = ConfigDict(frozen=True)`, immutable.

```python
class BankTxn(BaseModel):
    bank_id: str              # BNK-000001
    posted_at: datetime       # timezone-aware UTC
    amount_paise: int         # integer paise, never float
    utr: str | None           # 22-char UTR, may be missing
    narration: str            # free text, may contain payout_id substring

class GatewayPayout(BaseModel):
    payout_id: str            # pout_xxxxxxxxxxxxx (Razorpay format)
    created_at: datetime
    settled_at: datetime | None
    amount_paise: int
    fee_paise: int
    tax_paise: int
    utr: str | None
    status: Literal["processed", "reversed", "failed"]

class LedgerEntry(BaseModel):
    ledger_id: str            # LED-000001
    entry_date: date
    amount_paise: int         # signed: credit +, debit -
    reference: str            # order_id or payout_id
    account: str              # e.g., "settlements_receivable"

class MatchTriple(BaseModel):
    bank_id: str | None
    payout_id: str | None
    ledger_id: str | None
    confidence: float         # 0.0-1.0
    source: Literal["deterministic", "agent"]
    fields_matched: list[str] # ["utr", "amount_paise", "date_pm_1"]
    reason: str               # human-readable

class ExceptionRecord(BaseModel):
    row_ids: list[str]
    bucket: Literal["drift", "timing", "missing_utr", "duplicate",
                    "refund", "orphan_bank", "orphan_ledger"]
    severity: Literal["low", "medium", "high"]
    proposed_action: str
```

**Money = integer paise. Never float.** Prevents 0.1 + 0.2 drift bugs.

**Timestamps = timezone-aware UTC.** Prevents cutoff bugs.

---

## 7. Synthetic Data Spec

**Goal:** hard enough to be honest, structured enough to be gradable.

Defect mix (100 records baseline):

| Defect | % | Detection method | Expected outcome |
|--------|---|------------------|------------------|
| Clean 3-way match | 60 | deterministic UTR+amount | matched |
| Paise drift +/- Rs 0.50 | 10 | agent fuzzy (amount tolerance) | matched (drift bucket) |
| Date skew +/- 2 days | 10 | agent (utr match, date fuzzy) | matched (timing bucket) |
| Missing UTR one side | 8 | agent (narration parse, amount+date) | matched OR missing_utr |
| Duplicate payout | 5 | rule (2 payouts, 1 bank) | flagged duplicate |
| Refund/reversal pair | 5 | rule (offsetting entries) | matched pair, refund bucket |
| Orphan bank credit | 2 | residual | orphan_bank exception |

**Seed control:** `--seed 42` produces byte-identical CSVs. Enforced by test.

**Ground truth format:** every generated row carries a `_truth_label` column stripped before pipeline input. Kept in `ground_truth.csv` for the reporter.

**Anti-cheating:** agent never sees `_truth_label`. Enforced by test asserting label absence in serialized prompt.

---

## 8. Deterministic Matcher

**Rule stack (highest confidence first):**
1. Exact UTR match across all 3 sources -> match, confidence 1.0
2. UTR match on 2 sources + amount match on 3rd -> match, 0.95
3. Amount + date exact match, no UTR -> candidate (not auto-matched)
4. Duplicate detection: same `(utr, amount)` appearing >1 in payouts -> flag
5. Refund detection: `(amount, -amount)` pair in ledger within 7 days -> pair

Residual: everything else -> agent.

**Property:** matcher must have **zero false positives** on synthetic set. Enforced by test.

---

## 9. LLM Agent Spec

**Model:** `claude-haiku-4-5-20251001`

**Prompt structure (with prompt caching):**

```
[CACHED SYSTEM]
You are a reconciliation assistant. You match bank transactions to gateway
payouts to ledger entries. You MUST use the propose_match tool. You MUST
cite specific fields matched. You MUST NOT invent IDs not in the input.
If uncertain, return propose_match with confidence < 0.5.

<schema>
{JSON schemas for BankTxn, GatewayPayout, LedgerEntry}
</schema>

<rules>
- amount_paise must match exactly OR differ by <=50 paise (mark as "drift")
- dates may differ by <=2 calendar days (mark as "timing")
- UTR match is strongest signal
- Never match if amounts differ by >1%
</rules>
[/CACHED SYSTEM]

[USER, per residual batch of <=5 rows]
Candidates: {residual JSON}
Full source data: {sources JSON}
```

**Tool definition:**

```python
propose_match = {
    "name": "propose_match",
    "input_schema": {
        "type": "object",
        "required": ["bank_id", "payout_id", "ledger_id",
                     "confidence", "fields_matched", "reason"],
        "properties": {
            "bank_id": {"type": ["string", "null"]},
            "payout_id": {"type": ["string", "null"]},
            "ledger_id": {"type": ["string", "null"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "fields_matched": {
                "type": "array",
                "items": {"enum": ["utr", "amount_paise", "date",
                                   "narration", "reference"]},
                "minItems": 1
            },
            "reason": {"type": "string", "maxLength": 200}
        }
    }
}
```

**Batching:** <=5 residuals per call. Reason: keeps context small, cache-hit rate high, error blast radius small.

**Retry:** exponential backoff on 429/500. Hard cap 3 retries.

**Cost budget:** enforce `MAX_LLM_COST_USD` env var. Halt if exceeded.

---

## 10. Guardrail

Reject agent proposal if ANY:
- `confidence < 0.70`
- `len(fields_matched) < 2`
- Any ID in proposal not present in source data (hallucination check)
- Proposed amount delta > 1%
- Proposed date delta > 2 days

Rejected proposals -> residual -> exception classifier.

**Guardrail is a pure function.** Tested in isolation with hand-crafted proposals.

---

## 11. Exception Classifier

Deterministic bucketing of residuals into 7 labels. Rule-based, no LLM. Reason: classifier itself must be verifiable; can't have LLM grading LLM.

```
drift          -> amount within +/- 50p, all else matches
timing         -> utr matches, dates >2d apart
missing_utr    -> amount+date match, one side missing UTR
duplicate      -> 2 payouts, 1 bank, same amount
refund         -> offsetting ledger pair
orphan_bank    -> bank credit, no payout or ledger candidate
orphan_ledger  -> ledger entry, no bank or payout
```

Each bucket has a **proposed action** template ("investigate cutoff", "request UTR from bank", etc.).

---

## 12. Reporting & Observability

### 12.1 Reports

**`report.json`** — machine-readable:
```json
{
  "run_id": "uuid",
  "config": { "seed": 42, "n": 100, "model": "haiku-4-5" },
  "throughput": {
    "rows_total": 300,
    "wall_clock_seconds": 12.4,
    "rows_per_second": 24.2,
    "llm_tokens_input": 4210,
    "llm_tokens_output": 812,
    "llm_calls": 8,
    "cost_usd": 0.0034
  },
  "accuracy": {
    "match_rate": 0.92,
    "precision": 0.98,
    "recall": 0.94,
    "false_positives": 1,
    "false_negatives": 6
  },
  "buckets": {
    "matched_deterministic": 60,
    "matched_agent": 32,
    "drift": 8,
    "timing": 6,
    "missing_utr": 4,
    "duplicate": 3,
    "refund": 3,
    "orphan_bank": 2,
    "orphan_ledger": 0
  },
  "exceptions": [ { "row_ids": ["..."], "bucket": "...", "action": "..." } ]
}
```

**`report.md`** — human-readable summary with same numbers + a table of every unresolved exception with row IDs. Honest: unresolved count is prominent, not buried.

### 12.2 Observability

- **Logs:** structlog JSON to stdout. Every pipeline stage emits `stage_start` / `stage_end` with duration.
- **Metrics:** prometheus counters in-process:
  - `recon_rows_processed_total{stage}`
  - `recon_matches_total{source}`
  - `recon_llm_tokens_total{direction}`
  - `recon_llm_cost_usd_total`
  - `recon_exceptions_total{bucket}`
- **Traces:** every agent call gets a `trace_id`; logged with request/response.
- **Cassettes:** every API call recorded in `cassettes/`, replayed in tests.

### 12.3 What "observable" means for a beginner

Anyone running `python -m src.cli run --n 60 --seed 42` gets:
- Live progress log
- Final JSON + MD report
- `cassettes/` shows exactly what the LLM saw and returned
- `data/ground_truth.csv` shows what the correct answer was

Zero black-box steps. Every LLM decision auditable.

---

## 13. Security

Threat model: local dev tool, but sloppy handling of a real API key or a real CSV export could leak.

| Threat | Mitigation |
|--------|------------|
| API key leak | `.env` in `.gitignore`; `.env.example` template only; startup check refuses to run if key logged |
| PII in real data | Only synthetic data in repo; `data/` gitignored; README warns against dropping real CSVs |
| Prompt injection via narration field | Narration passed as data field in tool schema, not concatenated into prompt; length capped 200 chars; strip control chars |
| Cost blowout | `MAX_LLM_COST_USD` env var, halts run if exceeded |
| Log leakage | structlog redactor for `api_key`, `authorization` fields |
| Dependency supply chain | `uv.lock` committed; `pip-audit` in CI |
| Path traversal in CSV path arg | pathlib resolve + refuse paths outside `data/` |

**Never done:**
- No `eval()` / `exec()` on any input
- No shell out with user-controlled args
- No dynamic import from data

---

## 14. Verification Infrastructure

**Every task has a machine-checkable Definition of Done.** Below is the matrix. Each row must pass before phase is marked complete.

### 14.1 Phase 1 — Generator

| Task | Verification | DoD |
|------|--------------|-----|
| Schema defined | `mypy --strict src/schema.py` | 0 errors |
| Generator deterministic | `test_generator.py::test_seed_stability` | Two runs with seed=42 produce identical SHA256 of CSVs |
| Defect mix correct | `test_defects.py::test_defect_distribution` | Each bucket within +/- 2% of target for n=1000 |
| Ground truth complete | `test_generator.py::test_ground_truth_covers_all` | Every generated row has exactly one truth label |
| No PII | `test_generator.py::test_no_real_utrs` | Regex refuses UTRs matching known bank patterns |

### 14.2 Phase 2 — Deterministic Matcher

| Task | Verification | DoD |
|------|--------------|-----|
| Zero false positives | `test_match_rules.py::test_zero_fp` | On seed=42 batch, every deterministic match agrees with ground truth |
| Recall on clean subset | `test_match_rules.py::test_clean_recall` | >=95% of clean_match rows matched |
| Duplicate detection | `test_match_rules.py::test_duplicates` | All injected duplicates flagged |
| Refund pairing | `test_match_rules.py::test_refunds` | All refund pairs identified |

### 14.3 Phase 3 — Agent

| Task | Verification | DoD |
|------|--------------|-----|
| Tool call shape | `test_agent.py::test_tool_schema` | Every response uses `propose_match` tool, validates against schema |
| No hallucinated IDs | `test_agent.py::test_ids_in_source` | 100% of proposed IDs present in input |
| Deterministic under cassette | `test_agent.py::test_replay` | Same cassette -> same output |
| Cost tracking | `test_agent.py::test_cost_recorded` | `report.json.throughput.cost_usd > 0` |
| Ground truth NOT in prompt | `test_agent.py::test_no_leak` | Grep `_truth_label` in serialized prompt -> empty |

### 14.4 Phase 4 — Guardrail + Classifier + Report

| Task | Verification | DoD |
|------|--------------|-----|
| Guardrail rejects known-bad | `test_guardrail.py::test_reject_low_conf` | Confidence 0.5 proposal -> rejected |
| Guardrail rejects hallucination | `test_guardrail.py::test_reject_missing_id` | Proposal with fake ID -> rejected |
| Classifier deterministic | `test_exceptions.py::test_bucket_stability` | Same input -> same buckets |
| Report math correct | `test_report.py::test_precision_recall` | Hand-computed 4x4 confusion matrix matches reporter output |
| Report round-trip | `test_report.py::test_json_schema` | `report.json` validates against `report.schema.json` |

### 14.5 Phase 5 — E2E

| Task | Verification | DoD |
|------|--------------|-----|
| Full pipeline runs | `test_e2e.py::test_run` | Exit code 0, `report.json` written |
| Match rate bar | `test_e2e.py::test_match_rate` | >=90% on clean+drift+timing subset |
| Precision bar | `test_e2e.py::test_precision` | >=0.95 on agent proposals |
| Zero FP on orphans | `test_e2e.py::test_no_orphan_match` | Orphan rows never appear in matched set |
| Throughput bar | `test_e2e.py::test_throughput` | >=10 rows/sec end-to-end |
| Cost bar | `test_e2e.py::test_cost` | <=$0.01 for n=100 |
| Snapshot regression | `test_regression.py::test_report_snapshot` | Report matches golden file byte-for-byte |

### 14.6 CI gates

`.github/workflows/ci.yml` runs on every push:
1. `uv sync` — install
2. `ruff check && ruff format --check` — lint
3. `mypy --strict src` — types
4. `pytest --cov=src --cov-fail-under=85` — tests
5. `pip-audit` — deps
6. Post `report.md` as PR artifact for visual review

**Green CI = phase complete.** No manual "looks good to me."

### 14.7 When agent knows task is done

Definition of Done for the entire project:
- [ ] All 5 phases green
- [ ] Match rate >=90% (measured, not claimed)
- [ ] Precision >=95% on agent proposals
- [ ] Zero FP on orphans
- [ ] Cost <=$0.01/run for n=100
- [ ] E2E test passes on cassette (no live API needed)
- [ ] Snapshot test locked to golden report
- [ ] README lets a stranger reproduce all numbers in <=5 minutes

If any one fails, task is NOT done. No partial credit.

---

## 15. Scalability

Current design: 100 rows, seconds, cents. Not the point. But architecture must not preclude scaling.

| Dimension | Current | Path to 10x | Path to 100x |
|-----------|---------|-------------|--------------|
| Rows | 100 | 1000 (pandas fine) | 100k (switch to polars, chunk generator) |
| LLM calls | 8 | 80 (parallel with asyncio) | 800 (batch API, prompt cache mandatory) |
| Storage | CSV | Parquet | DuckDB / S3+Athena |
| Compute | Local Python | Same, larger batch | Ray / Modal for parallel agent calls |
| Cost | $0.003 | $0.03 | $0.30 (still cheap because Haiku + cache) |

**Non-breaking scale path:** async agent, polars swap-in, streaming CSV reader. Interfaces defined to allow it. Deliberately not built now (YAGNI).

---

## 16. Failure Modes — Where the Coding Agent Can Go Wrong

Explicit anti-pattern list. Every one has bitten someone before.

### 16.1 Money handling
- WRONG: Using `float` for money -> drift accumulates, matches fail silently
- RIGHT: Integer paise everywhere; convert to display only at report boundary

### 16.2 Time handling
- WRONG: Naive datetimes -> comparisons cross-tz become nonsense
- WRONG: Comparing dates with strings -> lexicographic sort != chronological in edge cases
- RIGHT: `datetime` with `tzinfo=UTC`; parse with `dateutil` explicitly

### 16.3 LLM misuse
- WRONG: Free-form text output parsed with regex -> brittle, silent failures
- WRONG: No tool schema -> model invents fields
- WRONG: Concatenating source data into prompt string -> prompt injection via narration
- WRONG: Trusting agent output without guardrail -> hallucinated matches ship as real
- WRONG: No cassette -> tests flake or cost money on every run
- WRONG: Grading LLM output with same LLM -> circular
- RIGHT: Tool use with strict schema; guardrail rejects; cassette replay; deterministic classifier

### 16.4 Ground-truth leakage
- WRONG: Passing full DataFrame to agent, which includes `_truth_label` column -> agent cheats
- WRONG: Filename with "answer" or "ground_truth" leaked to agent context
- RIGHT: Explicit projection at boundary; unit test asserts absence

### 16.5 Metrics dishonesty
- WRONG: Reporting only match rate, hiding false positives
- WRONG: Excluding unresolved rows from denominator ("we matched 100% of what we matched")
- WRONG: Cherry-picking a favorable seed
- RIGHT: Confusion matrix in report; total = |sources|; seed printed in every report

### 16.6 Determinism drift
- WRONG: Using `datetime.now()` in generator -> tests flake
- WRONG: Set iteration order assumed stable -> different Python builds break
- WRONG: Dict ordering assumed -> same
- RIGHT: All randomness through single `random.Random(seed)`; sorted iteration where order matters; test asserts SHA256 stability

### 16.7 Scope creep
- WRONG: Adding web UI "because it'd be cool"
- WRONG: Building auth for a local CLI
- WRONG: Adding a second loop before the first is verified
- WRONG: Adopting langchain "in case we need agents later"
- RIGHT: Ship the one loop, ship it verified, then stop

### 16.8 Fake completeness
- WRONG: TODO comments left in shipped code
- WRONG: Test asserts `True`, no actual check
- WRONG: Test wraps entire body in `try/except: pass`
- WRONG: Function returns hardcoded "success" without doing work
- RIGHT: CI runs mutation testing on >=1 module (mutmut) to catch fake tests

### 16.9 Config drift
- WRONG: Model version hardcoded in 3 places -> upgrade breaks one
- WRONG: Cost per token hardcoded -> SDK changes pricing, math wrong
- RIGHT: Single `config.py`; pricing pulled from anthropic SDK metadata where possible

### 16.10 Dependency rot
- WRONG: Unpinned deps -> CI green today, red tomorrow
- WRONG: Ignoring `pip-audit` warnings
- RIGHT: Lockfile committed; renovate/dependabot with human review

---

## 17. Do-Not List (Short Form)

Print this and tape it to the monitor.

1. **Do not** use `float` for money.
2. **Do not** parse LLM free-text output.
3. **Do not** pass ground truth into the agent context.
4. **Do not** grade the LLM with the LLM.
5. **Do not** ship a test that would pass if the function returned `None`.
6. **Do not** claim a match rate without printing the seed.
7. **Do not** silence exceptions with bare `except:`.
8. **Do not** commit `.env` or real customer data.
9. **Do not** add a feature not in this plan without editing this plan first.
10. **Do not** call the LLM without a cassette in tests.

---

## 18. End-to-End Testing Plan

Layered pyramid — cheap tests many, expensive tests few.

```
+---------------------------+
|  Regression (snapshot)    |  1 test, golden report
+---------------------------+
|  E2E (cassette)           |  ~5 tests
+---------------------------+
|  Integration              |  ~15 tests
+---------------------------+
|  Unit (per module)        |  ~60 tests
+---------------------------+
```

| Layer | Runs | Cost | Purpose |
|-------|------|------|---------|
| Unit | every save | 0 | Guards module contract |
| Integration | pre-commit | 0 | Pipeline stages compose correctly |
| E2E (cassette) | CI on every PR | 0 | Full pipeline behavior locked |
| E2E (live) | manual + nightly | ~$0.01 | Cassette refresh, catches API drift |
| Regression | CI on every PR | 0 | Report format doesn't drift |
| Mutation | weekly | 0 | Tests catch real bugs, not fake |

**Coverage target:** 85% overall, 95% for `guardrail.py` and `match_rules.py` (safety-critical).

**Test data:**
- Fixtures use small deterministic batches (n=10) for speed
- One golden E2E fixture (n=100, seed=42) for the bar test
- All fixtures committed under `tests/fixtures/`

---

## 19. Documentation Plan

Every doc has a single owner and a "last verified" date.

| Doc | Purpose | Owner | Refresh trigger |
|-----|---------|-------|-----------------|
| `README.md` | 5-min quickstart | project | Any CLI change |
| `PLAN.md` | This doc | project | Scope change |
| `ARCHITECTURE.md` | Diagrams + rationale | project | Interface change |
| `VERIFICATION.md` | How to verify each phase | project | Test change |
| `ANTI_SLOP.md` | Beginner checks | project | Never, stable |
| `CHANGELOG.md` | User-visible changes | project | Every merge |
| Docstrings | Function contracts | function author | Signature change |
| ADRs under `docs/adr/` | Non-obvious decisions | decider | New decision |

**Enforcement:** doc-lint CI job fails if a `.py` file changes without a corresponding docstring diff (for public functions) OR the CHANGELOG not touched.

### 19.1 README structure

1. What this is (2 sentences)
2. Quickstart (`uv sync && cp .env.example .env && python -m src.cli run --n 60 --seed 42`)
3. Sample report screenshot
4. How to verify the numbers (link to ANTI_SLOP.md)
5. Architecture (link to ARCHITECTURE.md)
6. License

---

## 20. Accountability

Because this is a solo build with an AI assistant, accountability = paper trail + machine gate.

| Artifact | What it proves |
|----------|----------------|
| Git commits (small, typed) | Change history, atomic revert possible |
| CI green badge | Machine agrees the code works |
| Cassettes in repo | LLM outputs auditable offline |
| Ground truth CSVs | Ground truth is data, not vibes |
| Snapshot golden report | Behavior locked, drift visible in diff |
| ADRs | Decisions documented with reasoning |
| Signed commits (optional) | Provenance |

**One rule:** any PR that changes accuracy numbers in the report must update the golden snapshot AND explain the delta in the PR body. No silent regressions.

---

## 21. Beginner's Anti-Slop Verification Guide

For someone who has never used Claude or seen this repo. Goal: convince them in 10 minutes that this is real work, not AI slop.

### Step 1 — Clone and run (2 min)
```
git clone <repo>
cd razor_pay
cp .env.example .env       # fill in ANTHROPIC_API_KEY
uv sync
python -m src.cli run --n 60 --seed 42
```

Expect: `reports/report.md` written. Open it.

### Step 2 — Check the numbers are real (2 min)

Open `reports/report.md`. Note the match rate.

Open `data/ground_truth.csv`. Count clean_match rows manually (or `wc -l`).

Open `reports/report.json`. Verify `accuracy.match_rate = matched / total` by hand. If the math doesn't add up, it's slop.

### Step 3 — Check the LLM isn't cheating (2 min)

Open `cassettes/e2e_run.yaml`. This is every prompt sent + response received. Search it for the string `_truth_label`. Should find nothing. If found -> agent was fed the answer.

Search for a proposed match ID in the response. Verify that ID exists in `data/bank.csv` or `data/payouts.csv`. If not -> hallucination.

### Step 4 — Change the seed, watch it work (1 min)
```
python -m src.cli run --n 60 --seed 999
```
Numbers change. Match rate stays within a few percent. Cost stays under $0.01. If it fails completely -> the earlier good result was a lucky seed.

### Step 5 — Break something on purpose (2 min)

Edit `src/match_rules.py`: change `amount == other.amount` to `amount != other.amount`. Rerun.

Match rate should collapse. Tests should fail. If they don't -> the tests weren't real.

Revert.

### Step 6 — Read the exception list (1 min)

Open `reports/report.md`. Every unresolved row is listed with an ID and a bucket. Pick one. Open the source CSV, find that row. The reason it's unresolved should be obvious to you.

If you can't explain why any given exception is in that bucket -> the classifier is opaque.

### Slop red flags checklist

If any of these are true, the project is AI slop:
- [ ] Reports say "match rate: 99%" but don't say total or seed
- [ ] Cassettes directory missing -> tests hit live API -> non-reproducible
- [ ] Ground truth file missing -> accuracy claims unverifiable
- [ ] Tests all pass but changing core logic doesn't break them
- [ ] Match rate identical across all seeds -> deterministic where it shouldn't be, suggests fake
- [ ] Cost reported as $0.00 -> not actually calling the API
- [ ] Exception list is empty and match rate is 100% -> too good to be true, check for leakage
- [ ] Agent output has fields the tool schema doesn't allow -> tool use not enforced
- [ ] `README.md` describes features that don't exist in `src/`

If none of the above hold, the project is real work.

---

## 22. Timeline & Milestones

| Phase | Est. | Milestone gate |
|-------|------|----------------|
| P1: Generator | 2h | `pytest tests/test_generator.py` green + `test_defects.py` green |
| P2: Deterministic matcher | 1h | Zero-FP test green |
| P3: Agent + guardrail | 3h | Cassette replay green + hallucination test green |
| P4: Classifier + report | 1h | Snapshot test locked |
| P5: E2E + eval | 2h | All bars in Section 14.7 met |
| Docs | 1h | README + ANTI_SLOP verified by external reader |
| **Total** | **~10h** | All CI gates green, golden report committed |

---

## 23. Open Questions (resolve before coding)

1. **Cassette policy:** commit cassettes with real API responses redacted? Or pure synthetic responses? Recommend: real, redacted (higher fidelity).
2. **Currency scope:** INR only, or multi-currency? Recommend: INR only (razor_pay domain, one problem at a time).
3. **Ledger sign convention:** credits positive or negative? Recommend: signed, credits positive (accountant-friendly).
4. **Bar values negotiable?** 90% match rate is a floor, not a target. If we clear 95% clean, tighten it.

Answer these before Phase 1. Log answers as ADR-001..004.

---

**End of plan. Awaiting confirmation to start Phase 1.**
