# PLAN.md — Critical Review vs Track 04

**Reviewed:** PLAN.md (33KB, 23 sections)
**Against:** Track 04 — AI Finance Controller
**Verdict:** Strong engineering spine, **fails 4 of 10 requirement atoms**, contains **4 internal logical contradictions that make the stated metrics unreachable as specified**, and has **zero UI** while the current direction requires one.

---

## 1. Requirement Coverage Matrix

Track 04 decomposed into atomic, testable requirements.

| # | Requirement atom (verbatim source) | Status | Evidence / Gap |
|---|-----------------------------------|--------|----------------|
| R1 | "Build an **agent**" | PARTIAL | §9 is a single-shot classifier: one `propose_match` tool call per batch of <=5 rows. No loop, no tool-selection, no state, no retrieval. A one-turn structured-output call is not an agent. |
| R2 | "**closes** one finance-ops loop" | MISSING | Pipeline ends at `report.json`. Nothing is written back: no settlement status flip, no journal adjustment, no exception assignment, no human resolution path. The loop is *observed*, never *closed*. |
| R3 | "across a **50+ record** batch" | COVERED | §7 n=60-100 per source, 300 rows total. |
| R4 | "of **synthetic** data" | COVERED | §7 generator, seeded, defect mix table. |
| R5 | "reporting its **match rate**" | PARTIAL | §12.1 emits `match_rate` but the **denominator is never defined**. 300 source rows? 100 triples? matched-triples / expected-triples? Unfalsifiable as written. |
| R6 | "and the **exceptions it could not resolve**" | PARTIAL | §11 taxonomy is good, but §12.1 `buckets` mixes *resolved-with-annotation* (drift, timing, refund) with *genuinely unresolved* (orphan_bank, orphan_ledger). "Could not resolve" is therefore not readable off the report. |
| R7 | bar: "**Throughput**" | WEAK | §14.5 measures `>=10 rows/sec` on **cassette replay**. Replay throughput measures YAML parsing, not the system. No live-run throughput, no concurrency, no p50/p95 latency per LLM call. |
| R8 | bar: "**measured accuracy**" | PARTIAL | Precision/recall present, but (a) the **unit of measurement is undefined** (triple-level? link-level? row-level?), and (b) there is **no deterministic-only baseline**, so the LLM's marginal contribution is unmeasured — fatal given the track's own "verification not generation" thesis. |
| R9 | bar: "**honest exception list**" | MOSTLY | §12.1 exception array with row_ids; §16.5 metrics-dishonesty anti-patterns are excellent. Undermined only by R6's bucket conflation. |
| R10 | "**One cherry-picked match proves nothing**" | GAP | Single golden seed (42) in CI. Multi-seed is a *manual doc step* (§21 Step 4), not a gate. Exactly the exposure the track calls out. |

**Score: 3 covered / 4 partial / 3 missing-or-weak.**

---

## 2. Internal Contradictions — Metrics Unreachable As Specified

These are not style notes. As written, the plan **cannot produce the report it prints.**

### C1 — CRITICAL: the `timing` bucket is unreachable

- §7 injects date skew of **+/-2 days**.
- §9 prompt rule: "dates may differ by **<=2** calendar days (mark as timing)".
- §11 classifier: `timing -> utr matches, dates **>2d** apart`.

Injected skew (<=2d) always falls **inside** the match tolerance, so those rows match and never reach the classifier. The `timing: 6` line in the sample `report.json` can never be produced.

**Fix:** inject skew in `[3, 5]` days for the timing-exception cohort and `[1, 2]` days for a separate *tolerated-skew* cohort. Two cohorts, two expected outcomes.

### C2 — CRITICAL: `drift` sits on the boundary and is double-counted

- Generator injects **+/-50 paise**; matcher tolerance is **<=50 paise inclusive**. Every drift row sits exactly on the boundary — one off-by-one in a comparison flips the entire cohort.
- Worse: §12.1 counts `drift: 8` in `buckets` while §7 says drift rows are "matched (drift bucket)". The same 8 rows are simultaneously matched and bucketed as exceptions.

**Fix:** inject drift uniformly in `[1, 49]` paise (tolerated) and a separate `[80, 200]` paise cohort (must NOT match). Split the report into `resolved` and `unresolved` bucket maps.

### C3 — CRITICAL: gross vs net is unmodeled

`GatewayPayout` carries `amount_paise`, `fee_paise`, `tax_paise`. A bank credit for a settlement equals **net = amount - fee - tax**. §8 rule 1 matches on "amount match" without saying which amount. Either:

- the matcher compares gross to the bank credit, so every clean match fails, or
- fee/tax are decorative fields that no rule reads.

Both are wrong, and this is the most domain-visible error to a finance reviewer.

**Fix:** define `net_paise = amount_paise - fee_paise - tax_paise` as a computed property; bank credit matches **net**; ledger entry matches **gross** with fee/tax as separate ledger lines. Add a `fee_mismatch` exception bucket.

### C4 — CRITICAL: `MatchTriple` cannot express the ground truth it grades

`MatchTriple` is `(bank_id?, payout_id?, ledger_id?)` — strictly 1:1:1. The defect mix requires:

- **duplicate payout**: 1 bank to **2** payouts
- **refund/reversal pair**: **2** offsetting ledger entries

Neither is representable. The reporter therefore cannot compare pipeline output to ground truth for 10% of the batch.

**Fix:** `MatchGroup { bank_ids: list[str], payout_ids: list[str], ledger_ids: list[str], ... }` with an invariant that a *clean* group has length 1 in each. Grade at **link level** (bipartite edge decisions), which also resolves D6.

---

## 3. Defect Register

Severity: **BLOCK** = fix before coding · **HIGH** = fix in-phase · **MED** = fix before demo · **LOW** = cleanup.

| ID | Sev | Defect | Fix |
|----|-----|--------|-----|
| D1 | BLOCK | C1 timing bucket unreachable | Two skew cohorts (<=2d tolerated, 3-5d exception) |
| D2 | BLOCK | C2 drift boundary + double-count | Two drift cohorts; split resolved/unresolved buckets |
| D3 | BLOCK | C3 gross vs net unmodeled | `net_paise` computed; bank<->net, ledger<->gross; add `fee_mismatch` bucket |
| D4 | BLOCK | C4 `MatchTriple` cannot hold N:M truth | `MatchGroup` + link-level grading |
| D5 | HIGH | Sample `report.json` is arithmetically inconsistent (60+32=92 matched, buckets sum to 26, 92+26=118 — neither 100 triples nor 300 rows) | Regenerate the sample from a real run; add `test_report.py::test_totals_reconcile` asserting every row lands in exactly one terminal state |
| D6 | HIGH | `match_rate` denominator undefined; precision/recall unit undefined; "4x4 confusion matrix" is meaningless for binary link decisions | Define unit = **candidate link** (bank<->payout, payout<->ledger). Binary confusion matrix per link type, plus a group-level exact-match rate. Print every denominator. |
| D7 | HIGH | **No deterministic-only baseline.** LLM marginal lift is unmeasured | Mandatory ablation: `rules_only` vs `rules+agent` vs `agent_only`, same seeds, same report format. Headline the **delta**. |
| D8 | HIGH | Throughput bar measured under cassette replay, so it is fake | Separate `throughput_replay` (CI gate, correctness) from `throughput_live` (nightly: rows/s with concurrency, p50/p95 per call). Never headline the replay number. |
| D9 | HIGH | Single golden seed in CI, contradicting the track's own bar | `eval sweep --seeds 1..20`; report **mean, stdev, min, max** for every headline metric. Gate CI on the **worst** seed. |
| D10 | HIGH | Loop never closes (R2) | Add `closer.py`: idempotent write-back (settlement status, adjustment journal lines, exception assignment) with `--dry-run` and reversal by `run_id` |
| D11 | MED | Defect percentages do not yield integers at n=60 (2% of 60 = 1.2) | Largest-remainder allocation; `test_defects.py::test_allocation_sums_to_n` for n in {50, 60, 77, 100, 1000} |
| D12 | MED | §16.9 says pricing is "pulled from anthropic SDK metadata" — the SDK does **not** expose pricing | Dated constant in `config.py` with source URL and `last_verified`; test asserts non-zero and date present |
| D13 | MED | VCR.py against the anthropic SDK httpx client is brittle (streaming, connection reuse, header redaction) | Record/replay at the **httpx transport** layer; commit plain JSON fixtures. Greppable, and serves §21 Step 3 better than YAML. |
| D14 | MED | `mypy --strict` + pandas is a stub-fighting tax for 300 rows | Drop pandas. Frozen pydantic models + stdlib `csv` + dict indexes. Keeps §15's polars path open and removes the largest typing friction. |
| D15 | MED | Guardrail thresholds (`confidence<0.70`, `fields_matched<2`) are asserted, not derived | Threshold sweep emitting a precision/recall curve; commit `reports/threshold_sweep.json` as the justification |
| D16 | MED | Agent determinism unspecified | `temperature=0`, `top_p` unset, system-prompt hash logged per run; document that temp-0 is still not bit-deterministic — that is *why* cassettes and multi-seed variance exist |
| D17 | MED | Cost cap alone does not bound blast radius | Add `MAX_RESIDUALS`, `MAX_LLM_CALLS`, `MAX_PROMPT_BYTES`; halt with a typed error, never a silent truncate |
| D18 | MED | No run history or comparison artifact | `run_id`-keyed persistence plus `compare <run_a> <run_b>` emitting a metric delta table |
| D19 | LOW | §19 doc-lint CI ("`.py` change requires docstring diff") fires on whitespace commits | Drop it. Replace with ruff `D` rules: public functions must have docstrings. |
| D20 | LOW | `src/exceptions.py` and `ExceptionRecord` shadow builtin vocabulary | Rename module to `classify.py`, model to `ReconException` |
| D21 | LOW | `prometheus_client` in a batch CLI with no scraper is ceremony | Keep in-process counters, emit them **into `report.json`**; drop the HTTP exposition server |
| D22 | LOW | §22 10h estimate excludes UI, eval sweep, ablation, write-back | Re-estimated in IMPLEMENTATION_PLAN.md §9 |
| D23 | LOW | §8 "zero false positives on synthetic set" is a property of the generator, not a proof | State as: zero FP across the 20-seed sweep; label it empirical, not formal |
| D24 | GAP | **No UI.** §1 lists web UI as an explicit non-goal | Contradicts the current direction. See IMPLEMENTATION_PLAN.md. |
| D25 | GAP | No secret boundary once a browser client exists | `ANTHROPIC_API_KEY` never leaves the Python worker. The browser gets a read-only RLS-scoped anon key. Make this explicit in the threat model. |

---

## 4. What PLAN.md Gets Right (keep verbatim)

Do not lose these in the rewrite — they are the strongest parts of the document:

- §6 **integer paise, never float** — correct and non-negotiable
- §6 **tz-aware UTC everywhere**
- §16.4 **ground-truth leakage** anti-pattern, plus the "grep the serialized prompt" test
- §16.5 **metrics dishonesty** list, especially "excluding unresolved rows from the denominator"
- §16.8 **fake completeness** plus mutation testing to catch assert-True tests
- §17 the Do-Not list
- §21 the **Anti-Slop guide** — the single most differentiating artifact in the plan. Promote it to a *live page in the UI* with every check computed at render time, not a static markdown file.
- §13 prompt-injection-via-narration mitigation (data in tool schema, not string concatenation)

---

## 5. Resolutions to §23 Open Questions

| Q | Resolution | Rationale |
|---|-----------|-----------|
| 1. Cassette policy | **Real responses, redacted, captured at transport layer, committed as JSON** | Fidelity beats synthetic; JSON is greppable by a reviewer doing §21 Step 3. Redact `authorization`, `x-api-key`, `request-id`. |
| 2. Currency scope | **INR only.** A `currency` field is present on all models and validated `== "INR"` | One problem at a time; field presence keeps the multi-currency path open without building it. |
| 3. Ledger sign convention | **Signed, credits positive.** Enforced by a pydantic validator per account type | Accountant-readable; refund pairs sum to exactly 0, which is the detection rule. |
| 4. Bars negotiable | **No. Bars are floors, set from the 20-seed sweep's worst seed.** | Setting a bar from the mean is the cherry-pick the track warns about. Publish worst/mean/best; gate on worst. |

Log as ADR-001..004 before Phase 1.

---

## 6. Bottom Line

PLAN.md is a good engineering plan for the wrong shape of deliverable. It over-invests in CI ceremony (prometheus server, doc-lint, mypy plus pandas) and under-invests in the three things the track actually scores:

1. **Proving the agent adds value** — baseline ablation, absent
2. **Proving the number is not cherry-picked** — multi-seed sweep, manual only
3. **Closing the loop** — write-back and human resolution, absent

And it forbids the UI the demo now requires.

Proceed to `IMPLEMENTATION_PLAN.md` for the corrected, split build plan.
