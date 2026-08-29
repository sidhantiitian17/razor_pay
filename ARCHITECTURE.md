# Architecture & System Design

Institutional 3-way financial reconciliation engine (Bank Statement <-> Gateway Payout <-> General Ledger) with deterministic rule stacks, bounded LLM agent escalation, audit-grade state closures, and multi-seed evaluation harnesses.

---

## 1. System Topology

```
                  +---------------------------------------------------+
                  |             Source Data Ingestion                 |
                  |  Bank Statements | Gateway Payouts | GL Journals  |
                  +-------------------------+-------------------------+
                                            |
                                            v
                  +---------------------------------------------------+
                  |      Phase 1: Pure Core Matching Pipeline         |
                  |  1. Candidate Blocker (Recall 1.0, |C| < n^2/4)   |
                  |  2. Deterministic Rule Stack (Exact, Fuzzy, Pair) |
                  +-------------------------+-------------------------+
                                            |
                         +------------------+------------------+
                         |                                     |
                  (Resolved Matches)                   (Residual Unmatched)
                         |                                     |
                         v                                     v
                  +-------------+                     +-----------------+
                  | Match Groups|                     | Phase 2: Agent  |
                  +------+------+                     | Multi-turn LLM  |
                         |                            | Replay / Active |
                         |                            +--------+--------+
                         |                                     |
                         |                            (Proposed Matches)
                         |                                     |
                         |                                     v
                         |                            +-----------------+
                         |                            | Phase 3: Guard  |
                         |                            | Deterministic   |
                         |                            | Multi-field     |
                         |                            +--------+--------+
                         |                                     |
                         |                        +------------+------------+
                         |                        |                         |
                         |                   (Accepted)                 (Rejected)
                         |                        |                         |
                         +------------------------+                         v
                                     |                             +-----------------+
                                     v                             | Exception Class |
                            +-----------------+                    | 9 Target Buckets|
                            | Idempotent Close|                    +--------+--------+
                            | System Writeback|                             |
                            | Balanced Journal|                    (Open Exceptions)
                            +--------+--------+                             |
                                     |                                      v
                                     +------------------+-------------------+
                                                        |
                                                        v
                                          +---------------------------+
                                          | Phase 4: Grader & Reporter|
                                          | Link-level Confusion, CI  |
                                          | Frozen Schema Validation  |
                                          +-------------+-------------+
                                                        |
                                                        v
                                          +---------------------------+
                                          | Phase 5: Storage & Wire   |
                                          | SQLite / Supabase (12 tbl)|
                                          | Publisher & Async Worker  |
                                          +---------------------------+
```

---

## 2. Core Architectural Principles

### 2.1 Pure Core Isolation (`engine/core/**`)
- All business matching algorithms, entity models, math calculations, and metric graders are pure functions.
- **Zero I/O:** No network, filesystem, environment variables, or wall clocks inside `engine/core/**`.
- Enforced automatically in CI via `import-linter` (`Core purity KEPT`).

### 2.2 Grader & Measurer Separation
- `engine/core/grader.py` shares zero imports with `engine/core/matching/` or `engine/app/agent.py`.
- The evaluation measurer is completely decoupled from the candidate producer.

### 2.3 Strict Typing & Precision
- Money is strictly modeled as integer paise (`amount_paise: int`). Floating-point arithmetic is forbidden in financial calculations.
- Datetimes are tz-aware UTC. Date arithmetic operates strictly through calibrated window intervals (`timewin.py`).

### 2.4 Bounded Agent Escalation & Safety Guardrails
- LLM interaction is constrained by a bounded multi-turn loop with strict schema validation.
- Every LLM proposal is gated by a deterministic 5-stage guardrail:
  1. High confidence threshold (`confidence >= 0.70`).
  2. Multi-field corroboration (>= 2 matching attributes).
  3. Anti-hallucination validation (all referenced IDs must exist in candidate space).
  4. Delta bounded tolerance.
  5. Deterministic rule protection (cannot override existing deterministic matches).

### 2.5 Idempotent State Closure & Reversal
- Write-back closures never operate on open exceptions (I15).
- Every closure records before/after state snapshots enabling exact, complete reversal (`close --reverse`, I14).
- Re-running the pipeline on closed state produces 0 new closures (second-pass convergence, R2).

### 2.6 LLM Backend Selection & Disclosure
- The bounded agent loop (`engine/app/agent.py`) is backend-agnostic: it drives any client implementing the `LLMClient` protocol in `engine/ports/llm.py`.
- Two adapters implement that protocol:
  - `engine/adapters/llm_anthropic.py` — a live Anthropic Messages API client (optional `llm` extra; `import anthropic` is lazy so the core engine imports without it).
  - `engine/adapters/llm_heuristic.py` — a deterministic offline simulator used for tests, CI, and any environment with no API key.
- `engine/adapters/select.py::select_llm_client()` picks the backend: live Anthropic when `ANTHROPIC_API_KEY` is set **and** the `anthropic` package is installed, otherwise the heuristic simulator. It returns `(client, backend_name)`; the caller records `backend_name` verbatim in `config.agent_backend` on every published report (`"none" | "heuristic" | "live"`). The selection is never silent — a reviewer reading a report always knows whether "agent" numbers came from a real model.
- `agent.py` threads each turn's assistant `tool_use` blocks (with stable `toolu_*` ids) plus the paired `tool_result` back into the message history, so a live model reconstructs a schema-valid multi-turn transcript. The heuristic/mock clients only read the message tail and are unaffected.

### 2.7 Genuine Per-Run Ablation
- `engine/app/reporter.py::generate_report()` populates the `ablation` block by genuinely re-running the other rule/agent arms on the same dataset/seed (companion calls with `_include_ablation=False` to bound recursion). No arm is a hardcoded constant.
- The `random` arm is sourced from the real random matcher in `engine/eval/controls.py`.
- `engine/eval/sweep.py` and `engine/eval/ablation.py` opt out of this in-report recomputation (they already do their own multi-mode reruns), so the standalone sweep cost is unchanged. A single `engine.cli run` now does ~3-4x the pipeline work it used to.

---

## 3. Database Schema (12 Relational Tables)

The storage layer matches `contracts/migrations/001_init.sql`:
1. `runs` — Execution metadata and full report JSON.
2. `source_bank` — Bank statement transactions.
3. `source_payout` — Gateway payout records.
4. `source_ledger` — General ledger journal lines.
5. `truth_groups` — Ground-truth benchmark groups.
6. `match_groups` — Deterministic and agent resolved match groups.
7. `link_decisions` — Binary link classification decisions (TP, FP, FN, TN).
8. `exceptions` — Open exception tickets with evidence and proposed actions.
9. `agent_calls` — LLM call telemetry, tokens, cost, latency, prompts, and guardrail verdicts.
10. `closures` — Audit-grade system state transition journals.
11. `control_results` — Automated negative control outcomes.
12. `run_requests` — Background task execution queue with atomic row-locking.

---

## 4. Scalability Roadmap

| Scale | Volume | Strategy | Adaptation Seam |
|---|---|---|---|
| **Current** | ~400 rows | In-memory dict indexing & SQLite | `ports/store.py` |
| **10x** | 4,000 rows | Sorted-neighbourhood blocking & Postgres | `matching/blocker.py` |
| **100x** | 400,000 rows | LSH MinHash & Parquet/DuckDB batching | `adapters/store_sqlite.py` |
| **LLM Tier** | 1,200 calls | Async Batch API worker fan-out | `ports/llm.py` |
