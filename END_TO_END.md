# END_TO_END.md — Executable Runbook

**Invocation:** "implement END_TO_END.md"

This file is the only entry point. It is written for an autonomous coding agent. Read it top to bottom, then execute §5 in a loop until §14 is satisfied. Do not improvise an order.

**Project:** Track 04 — AI Finance Controller. 3-way settlement reconciliation, closed loop, measured accuracy, honest exception list.

---

## 1. Session Bootstrap (do this before anything else)

Execute in this exact order. Do not skip step 4.

1. Read `IMPLEMENTATION_PLAN.md` in full. It is the authority on **what** to build.
2. Read `PLAN_REVIEW.md` §3 and §5. It is the authority on **why** the design looks the way it does. Defect IDs (D1..D25) are referenced throughout.
3. Skim `PLAN.md` §6, §13, §16, §17 only. Everything else in that file is superseded — do not implement from it.
4. Read `PROGRESS.md` if it exists. **This is resume state.** If it exists, find the last phase marked `complete` and start at the next one. If it does not exist, create it from the template in §4 and start at P0.
5. Verify preconditions (§2). Stop and ask if a required one is missing.
6. Announce to the user: current phase, what it will produce, the check IDs that gate it. Then begin.

**Never re-run a completed phase.** `PROGRESS.md` plus git tags are the record. If a completed phase's checks now fail, that is a regression — open a `fix/` branch, do not restart the phase.

---

## 2. Preconditions

Check each. If a required one is missing, stop and ask the user — never attempt to create accounts or obtain credentials yourself.

| # | Precondition | Verify with | Needed from |
|---|--------------|-------------|-------------|
| 2.1 | Git installed, repo initialized | `git rev-parse --is-inside-work-tree` | P0 |
| 2.2 | GitHub remote configured | `git remote -v` | P0 |
| 2.3 | `gh` CLI authenticated | `gh auth status` | P0 |
| 2.4 | Python 3.11+ and `uv` | `uv --version` | P0 |
| 2.5 | Node 20+ and npm | `node -v` | P0 |
| 2.6 | `ANTHROPIC_API_KEY` in `.env` | `.env` present, key set | P3 |
| 2.7 | Supabase project URL + anon key + service key | `.env` entries present | P6 |
| 2.8 | `psql` available, or Supabase SQL editor access | `psql --version` | P0 check 0.6 |
| 2.9 | Lovable MCP reachable | `mcp__claude_ai_Lovable__get_me` | P7 |
| 2.10 | `gitleaks` installed | `gitleaks version` | every push |

**This repo is not yet a git repository.** `git init` is step 1 of P0 — before the first commit, not after.

**Deferred preconditions:** 2.6–2.9 are not needed for P0–P2. Start the work; ask for each at the phase that needs it, not up front.

---

## 3. Document Graph

Know which file is authoritative for what. Never let two files disagree silently.

| File | Status | Authority over | Who edits |
|------|--------|----------------|-----------|
| `END_TO_END.md` | **runbook** | Execution order, protocols, prohibitions | Human only |
| `IMPLEMENTATION_PLAN.md` | **authority** | Scope, data model, evaluation, phase checks | Agent, only via §11.13 protocol |
| `PLAN_REVIEW.md` | rationale | Why decisions were made; defect IDs | Frozen |
| `PLAN.md` | historical | Money/time invariants, anti-patterns only | Frozen |
| `PROGRESS.md` | **state** | What is done, failed, blocked | Agent, every phase |
| `docs/adr/ADR-*.md` | decisions | One decision each, with rationale | Agent, on any deviation |
| `docs/EVALUATION.md` | generated | Methodology as shipped (mirrors plan §4) | Agent, P5 |
| `docs/FALSIFICATION.md` | generated | The 6 refutation conditions (plan §4.10) | Agent, P5 |
| `ARCHITECTURE.md` | generated | Diagrams + interface rationale | Agent, P13 |
| `VERIFICATION.md` | generated | How a human reruns every check | Agent, P13 |
| `ANTI_SLOP.md` | generated | Reviewer's 10-minute guide (from `PLAN.md` §21) | Agent, P13 |
| `README.md` | generated | Quickstart, headline numbers, how to refute them | Agent, P13 |
| `CHANGELOG.md` | generated | One entry per merged phase | Agent, every phase |

**Rule:** if implementation must deviate from `IMPLEMENTATION_PLAN.md`, write the ADR **first**, edit the plan **second**, then code. Never code a deviation and document it afterwards.

---

## 4. `PROGRESS.md` — the resume ledger

Create at P0 start. Update at every phase boundary and every blocker. This is what lets the run survive a session ending.

```markdown
# PROGRESS

Repo: <github url>
Lovable project id: <set at P7>
Lovable preview url: <set at P7>
Supabase project ref: <set at P6>
Holdout seed set in use: 101-120
Holdout burns: none

| Phase | Owner | Status | Checks | Branch | Commit | Tag | Date |
|-------|-------|--------|--------|--------|--------|-----|------|
| P0 | CC | complete | 0.1-0.13 PASS | phase/P0-contracts | a1b2c3d | p0-complete | 2026-08-24 |
| P1 | CC | in_progress | 1.1-1.6 PASS, 1.7 FAIL(1/3) | phase/P1-generator | - | - | - |

## Blockers
(none)

## Deviations
(none — each needs an ADR link)
```

Status vocabulary, use exactly these: `not_started` · `in_progress` · `blocked` · `complete`.

---

## 5. The Phase Loop — run this verbatim for every phase

The algorithm does not change between phases. Only the inputs do.

```
FOR phase IN [P0, P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13]:

  0. If PROGRESS says complete -> skip.
     If PROGRESS says blocked  -> stop, report to user.

  1. PLAN
     Read that phase's section in IMPLEMENTATION_PLAN.md.
     Restate: deliverables, check IDs, exit gate.
     Write the check runner FIRST: scripts/checks/<PHASE>.sh   (§8)
     PROGRESS: status = in_progress.

  2. BRANCH
     git checkout main && git pull
     git checkout -b phase/<PHASE>-<slug>

  3. TESTS FIRST   (engine phases)
     Spawn tdd-guide (§6). Write the phase's tests from the check table.
     Run them. They MUST fail. A test passing before implementation is a fake test.
     Commit: test(<scope>): add failing tests for <PHASE>

  4. IMPLEMENT
     Main thread does the work. Small commits, one logical unit each (§9.3).
     Engine phase -> write Python here.
     UI phase     -> send a Lovable message (§7). Never hand-write UI code.

  5. VERIFY
     bash scripts/checks/<PHASE>.sh
     Every check prints PASS or FAIL with its ID. Exit 0 required.
     On FAIL -> §10 three-strike protocol.

  6. REVIEW
     Spawn that phase's review agents IN PARALLEL (§6.2).
     Fix every CRITICAL and HIGH. MEDIUM when cheap. Record LOW in PROGRESS.
     Re-run scripts/checks/<PHASE>.sh after fixes.

  7. DOCUMENT
     Update CHANGELOG.md. Write any ADR the phase produced.
     PROGRESS: checks, commit, status.

  8. SHIP  (§9)
     gitleaks detect --no-git      -> 0 findings required
     bash scripts/checks/all.sh    -> full regression, exit 0 required
     git push -u origin phase/<PHASE>-<slug>
     gh pr create   (body template §9.4)
     CI green -> squash merge -> tag <phase-lower>-complete -> push tags

  9. ADVANCE
     PROGRESS: status = complete.
     One line to the user: phase, checks passed, tag.
     Continue immediately to the next phase. Do not wait for permission.
```

**Continuity rule:** the loop is continuous. Never stop between phases to ask "shall I continue?". Stop only for §12.

### 5.1 Interleave schedule (Track A engine, Track B UI)

One session is serial, but Lovable builds asynchronously. Use its build time.

| Step | Action |
|------|--------|
| 1 | P0 engine contracts → tag `p0-complete` |
| 2 | Create Lovable project, set knowledge, **send P7** (§7.1) |
| 3 | P1 engine, while Lovable builds P7 |
| 4 | Verify P7 → **send P8** |
| 5 | P2 engine |
| 6 | Verify P8 → **send P9** |
| 7 | P3 engine |
| 8 | Verify P9 → **send P10** |
| 9 | P4 engine |
| 10 | Verify P10 → **send P11** |
| 11 | P5 engine |
| 12 | Verify P11 |
| 13 | P6 engine (publisher + worker) |
| 14 | P12 integration → P13 hardening |

P0 must be tagged before step 2 — Lovable consumes `report.d.ts`, generated from the frozen schema.

---

## 6. Agent Roster and Spawn Policy

### 6.1 When to spawn

Spawn a subagent when the task is **bounded, read-heavy, and parallelizable**. Do the implementation yourself in the main thread — you hold the context.

**Never spawn for:** a single-file edit, a rename, running a test, reading a file you can read yourself.

### 6.2 Roster per phase

| Phase | Before implementation | After implementation (parallel, one message) |
|-------|----------------------|---------------------------------------------|
| P0 | `everything-claude-code:architect` — review the frozen schema and model set against `IMPLEMENTATION_PLAN.md` §3 | `everything-claude-code:database-reviewer` (SQL + RLS), `everything-claude-code:security-reviewer` (RLS posture, secret boundary) |
| P1 | `everything-claude-code:tdd-guide` | `everything-claude-code:python-reviewer`, `everything-claude-code:code-reviewer` |
| P2 | `tdd-guide` | `python-reviewer`, `code-reviewer` |
| P3 | `tdd-guide` | `security-reviewer` (prompt injection, secrets, cassette redaction), `python-reviewer`, `code-reviewer` |
| P4 | `tdd-guide` | `python-reviewer`, `code-reviewer` |
| P5 | `tdd-guide` | `python-reviewer`, `code-reviewer`, `everything-claude-code:silent-failure-hunter` |
| P6 | `tdd-guide` | `database-reviewer`, `security-reviewer` |
| P7 | `everything-claude-code:a11y-architect` — set the a11y bar before Lovable builds | `everything-claude-code:e2e-runner` — author the Playwright specs |
| P8–P11 | — | `e2e-runner` (specs), `everything-claude-code:typescript-reviewer` (on the mirrored `ui/`) |
| P12 | — | `code-reviewer`, `e2e-runner` |
| P13 | — | `security-reviewer`, `everything-claude-code:performance-optimizer`, `everything-claude-code:doc-updater` |

### 6.3 Spawn rules

1. **Max 3 concurrent.** Put independent spawns in one message so they run in parallel.
2. **Give each agent the phase's check IDs**, not vague instructions. "Verify checks 3.1–3.13 in `IMPLEMENTATION_PLAN.md` §7 P3" beats "review the agent code".
3. **Relay findings, do not paste transcripts.** The agent's report is not shown to the user.
4. **Never let a subagent commit or push.** Subagents propose; the main thread commits.
5. **Do not re-delegate.** If you are the subagent, execute.
6. **A subagent's claim is not evidence.** Re-run the check yourself before marking PASS.

---

## 7. Lovable MCP Protocol

### 7.1 One-time setup (immediately after `p0-complete`)

```
1. mcp__claude_ai_Lovable__get_me
   -> confirms auth

2. mcp__claude_ai_Lovable__list_workspaces
   -> if more than one, ASK the user which. Never guess.

3. mcp__claude_ai_Lovable__create_project
   workspace_id:     <chosen>
   initial_message:  <P7 prompt sketch from IMPLEMENTATION_PLAN.md §8,
                      prefixed with the 8 hard rules from its §14>
   -> returns projectId, editor_url, preview_url
   -> RECORD ALL THREE IN PROGRESS.md IMMEDIATELY

4. mcp__claude_ai_Lovable__render_project_widget
   projectId: <id>
   -> shows the user live build progress

5. mcp__claude_ai_Lovable__set_project_knowledge
   content: <the 8 hard rules from IMPLEMENTATION_PLAN.md §14, verbatim>
   -> persists across every message; set once, never restate per message

6. mcp__claude_ai_Lovable__enable_database
   -> apply contracts/migrations/001_init.sql
   -> verify with mcp__claude_ai_Lovable__get_database_status
```

**Migration ownership:** the SQL is authored by Claude Code in P0. Lovable applies it **verbatim**. Never ask Lovable's agent to design the schema. If Lovable reports a migration error, fix the SQL in this repo and resend — never let Lovable patch it in place.

### 7.2 Per UI phase (P8–P11)

```
1. mcp__claude_ai_Lovable__send_message
   projectId: <id>
   message:   <that phase's prompt sketch from IMPLEMENTATION_PLAN.md §8, verbatim>

   Use plan_mode=true FIRST for P9 and P11 (the two most complex screens).
   Read the plan back, correct it, then send the real message.

2. Wait for completion:
   mcp__claude_ai_Lovable__get_project    (status)
   mcp__claude_ai_Lovable__get_message    (a specific message)

3. Review what changed:
   mcp__claude_ai_Lovable__get_diff

4. Mirror into this repo for CI:
   mcp__claude_ai_Lovable__list_files
   mcp__claude_ai_Lovable__read_file      (each changed file)
   -> write under ui/
   -> commit: chore(ui): sync Lovable P8 output

5. VERIFY (§8.3): run that phase's Playwright specs against preview_url.

6. On failure -> follow-up send_message naming the failing check ID and the
   expected behaviour. NEVER hand-edit a file under ui/.
```

**Preferred alternative to step 4:** Lovable's native GitHub sync, enabled once by the user in the Lovable editor. Ask for it — it removes the manual mirror entirely. Until then, `list_files` + `read_file`.

### 7.3 Lovable hard rules

- **Never** put a secret, API key, service-role key, or real data into a Lovable message.
- **Never** hand-edit files Lovable owns. Desync is silent and expensive.
- **Never** let Lovable invent the database schema, the metric names, or the TypeScript types. All three are P0 contracts.
- **Always** resend `report.d.ts` when `schema_version` bumps.
- Each `send_message` spends the user's Lovable credits. Batch a phase into one well-specified message rather than five vague ones.

---

## 8. Verification Protocol

### 8.1 Check runners (authored in P0, extended each phase)

`scripts/checks/<PHASE>.sh` — one per phase. Contract:

- Runs each check from that phase's table, in ID order.
- Prints exactly one line per check: `PASS <id> <name>` or `FAIL <id> <name> :: <shortest decisive line>`.
- Exits 0 only if every check passed.
- Never mutates repo state. Never calls a live API unless the check requires it (5.11, 5.14 live arm).

```bash
#!/usr/bin/env bash
set -uo pipefail
fails=0
check() {  # check <id> <name> <command...>
  local id="$1" name="$2"; shift 2
  if out=$("$@" 2>&1); then
    echo "PASS $id $name"
  else
    echo "FAIL $id $name :: $(echo "$out" | grep -m1 -E 'Error|assert|FAILED|error' || echo "$out" | tail -1)"
    fails=$((fails+1))
  fi
}

check 3.1 tool_schema  uv run pytest tests/test_agent.py::test_tool_schema -q
check 3.2 loop_bounded uv run pytest tests/test_agent.py::test_loop_bounded -q
# ... one line per check ID in the phase table

[ "$fails" -eq 0 ] || { echo "PHASE FAILED: $fails check(s)"; exit 1; }
echo "PHASE PASSED"
```

`scripts/checks/all.sh` runs every runner up to the current phase — the regression net. Run before every PR merge.

### 8.2 What counts as a pass

- The runner exits 0. That is the entire definition.
- A check that cannot run (missing credential or service) is **BLOCKED**, not passed. Record it in `PROGRESS.md` and stop the phase.
- **Never** mark a check N/A, `xfail` it, skip it, or delete it to move on. If a check is genuinely wrong, that needs an ADR and a plan edit (§11.13), not a quiet removal.

### 8.3 UI verification

Specs live in `tests_ui/`, authored by `e2e-runner`, run by the main thread:

```bash
LOVABLE_PREVIEW_URL=<preview_url> npx playwright test tests_ui/<spec> --reporter=line
```

The no-fabrication specs (8.1, 8.6, 10.6, 11.2) are load-bearing. They read the fixture JSON and diff it against the DOM. If they are weak, the whole UI track is unverified.

---

## 9. Git Protocol

### 9.1 Repository setup (P0, once)

```bash
git init
# .gitignore FIRST, before any other file is added
printf '.env\n.venv/\n__pycache__/\nnode_modules/\ndata/\nreports/*.json\n!reports/golden_report.json\n.pytest_cache/\n' > .gitignore
printf '* text=auto eol=lf\n*.sh text eol=lf\n' > .gitattributes
git add .gitignore .gitattributes
git commit -m "chore: initialize repository with ignore rules"
git branch -M main
git remote add origin <url>
git push -u origin main
```

Install a pre-commit hook running `ruff check`, `mypy`, and `gitleaks` on staged files. Never bypass it with `--no-verify`.

### 9.2 Branching

- `main` — always green, always deployable. **Never commit directly.**
- `phase/P3-agent-guardrail` — one branch per phase.
- `fix/P2-blocker-recall` — regression on a completed phase.
- Delete the branch after merge.

### 9.3 Commits

Conventional Commits, one logical unit per commit. A commit touching the generator, the matcher, and the README is three commits.

```
<type>(<scope>): <imperative subject, <=72 chars>

<what changed and why, wrapped at 72 — not how; the diff shows how>

Phase: P3
Checks: 3.1-3.10 PASS
Refs: R1, D17
```

Types: `feat` `fix` `test` `refactor` `docs` `chore` `perf` `ci`.
Scopes: `generator` `matcher` `agent` `guardrail` `classify` `closer` `grader` `report` `eval` `publisher` `worker` `ui` `contracts` `ci`.

Rhythm within a phase:

1. `test(agent): add failing tests for bounded tool loop` — red
2. `feat(agent): implement bounded multi-turn tool loop` — green
3. `feat(agent): add turn and cost accounting`
4. `refactor(agent): extract tool dispatch into registry`
5. `docs(agent): document loop contract and turn limits`

Per the session harness, end commit messages with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: <session url>
```

If the user's `~/.claude/settings.json` disables attribution, omit both lines — do not argue with the setting.

### 9.4 Pull request

Open at phase end, after the runner is green locally.

```bash
gitleaks detect --no-git             # 0 findings required
bash scripts/checks/all.sh           # exit 0 required
git push -u origin phase/P3-agent-guardrail
gh pr create --title "P3: agent loop, guardrail, replay" --body-file .pr-body.md
```

Body template:

```markdown
## Phase
P3 — Agent Loop, Guardrail, Replay

## Requirement atoms advanced
R1 (agent is a real loop), R8 (guardrail threshold from a PR curve)

## Verification
`bash scripts/checks/P3.sh` -> PASS (13/13)

| Check | Name | Result |
|-------|------|--------|
| 3.1 | tool_schema | PASS |
| ... | ... | ... |

Exit gate 3.4 + 3.6 + 3.11: satisfied.

## Metric impact
match_rate (holdout, rules_agent): 0.61 -> 0.92
precision_cost: -0.011   (stated, not hidden)
Golden snapshot updated: yes — delta explained below.

## Delta explanation
<required whenever a reported number changes — PLAN.md §20>

## Risks / follow-ups
<or "none">

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

**Any PR that changes a reported metric must update the golden snapshot AND explain the delta.** A PR that moves a number without an explanation is rejected by protocol, not by taste.

### 9.5 Merge and tag

```bash
gh pr merge --squash --delete-branch
git checkout main && git pull
git tag p3-complete && git push --tags
```

Tags are the resume anchor. `PROGRESS.md` records the tag; a fresh session trusts the tag over its own memory.

### 9.6 CI (`.github/workflows/ci.yml`, authored in P0)

On every push and PR:

```
uv sync
ruff check && ruff format --check
mypy --strict engine
lint-imports
pytest --cov=engine --cov-fail-under=85      # replay mode only, zero network
bash scripts/checks/all.sh
pip-audit
gitleaks detect --no-git
cd ui && npx tsc --noEmit
```

`eval.yml` runs nightly: live throughput bench (5.11), negative controls (5.14), holdout sweep (5.5); posts `report.md` as an artifact. **Live API calls never run on PR CI** — cost and nondeterminism.

---

## 10. Failure Protocol — three strikes

When `scripts/checks/<PHASE>.sh` reports a FAIL:

| Strike | Action |
|--------|--------|
| 1 | Read the shortest decisive error line. Form one hypothesis. Fix. Re-run **only that check**. |
| 2 | A different hypothesis — not the same fix retried. Consider spawning the matching `*-build-resolver` or reviewer agent for a second read. Fix. Re-run. |
| 3 | **Stop.** Write the blocker into `PROGRESS.md`: check ID, exact error, both attempted fixes and why each failed, your best theory of the real cause. Report to the user. Do not proceed to the next phase. |

Never loop on the same failing command. Never widen a fix's blast radius to make a check pass. Never edit the check.

**Special case — the check reveals the plan is wrong, not the code:** stop, write an ADR, edit `IMPLEMENTATION_PLAN.md`, get user confirmation, then resume. This is the only legitimate route to changing a check.

---

## 11. What NOT To Do

Numbered so a reviewer can cite one.

1. **Do not start a phase before the previous phase's tag exists.** Tags are the gate, not your judgement.
2. **Do not edit a test to make it pass.** Fix the implementation. A test bent to accommodate broken code is the highest-severity failure in this project.
3. **Do not delete or regenerate the golden report** to silence a regression test. Update it only with a PR delta explanation (§9.4).
4. **Do not change a threshold, prompt, or rule after seeing holdout results** without an ADR and rotating the holdout seed set (`IMPLEMENTATION_PLAN.md` §4.4). Record the burn in `PROGRESS.md`.
5. **Do not commit** `.env`, real API keys, unredacted cassettes, `data/`, or anything matching a real bank UTR pattern.
6. **Do not hand-edit files Lovable owns.** Send a follow-up message instead.
7. **Do not let ground truth reach the agent.** No truth column, no cohort label, no filename containing `truth` — not even in a debug log that gets serialized.
8. **Do not use `float` for money.** Integer paise everywhere; format only at the display boundary.
9. **Do not headline replay throughput.** Replay is a correctness mode, not a performance claim.
10. **Do not sum resolved tags with unresolved buckets.** Disjoint vocabularies (`IMPLEMENTATION_PLAN.md` §3.6).
11. **Do not report a metric without its numerator, denominator, seed, and seed-set.**
12. **Do not mark a check N/A, xfail, or skipped** to move on. BLOCKED and stop, or fix it.
13. **Do not add a feature not in `IMPLEMENTATION_PLAN.md`.** Edit the plan first, with an ADR. This includes "small" additions — a nicer chart, an extra endpoint, a clever cache.
14. **Do not spawn more than 3 concurrent agents**, and never spawn one for work a single edit would do.
15. **Do not trust a subagent's "verified" claim.** Re-run the check yourself.
16. **Do not run live API calls in PR CI.**
17. **Do not force push, use `--no-verify`, or commit directly to `main`.**
18. **Do not proceed past three failed fix attempts.** Escalate (§10).
19. **Do not use `dangerouslyDisableSandbox`** or ask the user to skip permissions.
20. **Do not put secrets, real data, or customer information** into a Lovable message or a published Supabase row.
21. **Do not claim a phase complete while any check is BLOCKED.**
22. **Do not silently swallow an exception** anywhere in the engine. Typed errors, always.
23. **Do not optimize before P13.** No caching, no async, no polars, until the numbers are honest and the gates are green.
24. **Do not paste long raw logs** into the user-facing report. One decisive line.

---

## 12. Stop and Escalate

Stop the loop and ask the user only for these. Everything else: decide and continue.

| Condition | What to report |
|-----------|----------------|
| Three failed fix attempts on one check | Check ID, error, both hypotheses tried, your best theory |
| Missing credential or service (2.6–2.9) | Which one, which phase needs it, what is blocked until then |
| Holdout burn required | What you want to change, why, and that the seed set must rotate |
| Schema change needed after the P0 freeze | The change, the `schema_version` bump, what must be regenerated |
| A `security-reviewer` CRITICAL finding | The finding verbatim; do not proceed |
| Cost cap (`MAX_LLM_COST_USD`) hit | Spend so far, what remains, whether to raise it |
| Lovable errors twice on the same message | The error and the message you sent |
| More than one Lovable workspace | Ask which; never guess |
| A check appears wrong rather than the code | Your reasoning and the proposed ADR |

**Do not stop** to ask: whether to continue to the next phase, whether a commit message is good enough, whether to run a check, whether a MEDIUM review finding is worth fixing.

---

## 13. Take Care — hazards by area

### 13.1 Determinism
- One `random.Random(seed)` instance threaded through the generator. No module-level `random`, no `numpy.random` default.
- Sort before iterating anything whose order reaches output. Dict order is insertion order — not stable across a regenerated input.
- No `datetime.now()` inside `engine/core/**`. Time arrives through the `Clock` port.
- Verify check 1.2 (SHA stability) before trusting any downstream number.

### 13.2 Money and time
- Integer paise. Format only in `reporter` and the UI.
- `net = gross - fee - tax`, and the bank credit matches **net** (`IMPLEMENTATION_PLAN.md` §3.3). Reversing this silently zeroes the clean-match rate.
- Journal sets sum to exactly 0. Assert at construction, not at report time.
- Calendar-day deltas, never naive timedelta division. Cutoffs are the entire point of the `timing` bucket.

### 13.3 The agent
- `temperature=0`, no `top_p`. Log the system-prompt hash per run.
- Data goes into tool inputs, never concatenated into the prompt string. That is the prompt-injection boundary.
- Set `MAX_TURNS`, `MAX_RESIDUALS`, `MAX_LLM_CALLS`, `MAX_PROMPT_BYTES`, `MAX_LLM_COST_USD` before the first live call. Halt with a typed error; never truncate silently.
- Redact `authorization`, `x-api-key`, `request-id` from cassettes **before** committing, not after.

### 13.4 Evaluation honesty
- Tune on dev seeds (1–10). Report on holdout (101–120). Seed 42 is the regression snapshot and is never a claim.
- Publish `blocker_recall`. Below 1.0, every downstream precision claim is capped and must say so.
- Report `precision_cost` alongside `agent_lift` — especially when it is bad.
- If `agent_lift` is not positive, the honest deliverable is a report saying the rules alone sufficed. Ship that rather than tuning until the number looks good.

### 13.5 Security
- `.gitignore` before the first `git add`. A secret committed once is committed forever, even if deleted in the next commit.
- `gitleaks` before every push, not only before the PR.
- RLS on every table; anon has no write path. Verify with a real anon-key write attempt (check 6.6), not by reading the policy text.
- The service-role key lives only in the worker's environment. Grep `ui/src` for it every UI phase (check 7.7).

### 13.6 Windows specifics
- `.gitattributes` with `eol=lf` at repo init, or every `.sh` gets CRLF and fails in CI.
- Build paths with `pathlib`; never string-concatenate them.
- The Bash tool is Git Bash; the PowerShell tool is PowerShell 5.1, where `&&`, `??`, and `?:` are parser errors — use `;` with `if ($?)`.
- `psql` may not be on PATH. Falling back to the Supabase SQL editor is fine — record in `PROGRESS.md` that check 0.6 ran manually.

### 13.7 Cost and time
- Run the live throughput bench (5.11) on an otherwise idle machine, or p95 measures your own CPU contention.
- Replay mode for everything except 5.11, 5.14's live arm, and cassette refresh.
- Cassette refresh is a deliberate, reviewed act — it changes what every test sees.

### 13.8 Scope
- The plan is the scope. The most likely failure of this project is not a bug; it is building a second loop, a nicer chart, or a caching layer instead of finishing the exception list and the eval harness.
- When tempted, reread `IMPLEMENTATION_PLAN.md` §2.4 and `PLAN.md` §16.7.

---

## 14. Completion

The run is complete when **all** of the following hold. Verify each; never assert from memory.

- [ ] `PROGRESS.md` shows all 14 phases `complete`
- [ ] 14 tags exist: `p0-complete` … `p13-complete`
- [ ] `bash scripts/checks/all.sh` exits 0 on a clean checkout of `main`
- [ ] Every box in `IMPLEMENTATION_PLAN.md` §10 (Master DoD) is checked, each with the check ID proving it
- [ ] CI green on `main`; nightly `eval.yml` has run at least once and posted a report
- [ ] `gitleaks detect --no-git` on the full repo: 0 findings
- [ ] Lovable project deployed; preview URL recorded in `PROGRESS.md` and `README.md`
- [ ] Docs exist and are accurate: `README`, `ARCHITECTURE`, `VERIFICATION`, `ANTI_SLOP`, `EVALUATION`, `FALSIFICATION`, `CHANGELOG`, `docs/adr/*`
- [ ] A stranger following `README.md` reproduces every headline number in under 10 minutes (check 13.11)
- [ ] The Verify page passes on the golden fixture and **fails** on the poisoned one (check 10.6)

**Final report to the user** — one message, no ceremony:

1. Headline numbers with denominators and seed set: match rate, resolved/unresolved, precision and recall per link type
2. Agent lift over baseline, with precision cost
3. Live throughput and cost per 100 rows
4. Unresolved exception count by bucket — the honest list
5. All six negative-control verdicts
6. Repo URL, preview URL, and the single command that reruns everything

If a number disappoints, report it as measured. A measured 74% with a working exception list and six passing controls is what this track asks for. A claimed 99% is not.
