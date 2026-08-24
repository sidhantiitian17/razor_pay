-- Track 04 — AI Finance Controller
-- Supabase schema + RLS (§5.2)
-- Authored by Claude Code, applied by Lovable verbatim.
-- Idempotent: re-applying is safe.

-- ============================================================
-- Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engine_version TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0.0',
    config JSONB NOT NULL,
    report JSONB,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'complete', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS source_bank (
    bank_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    posted_at TIMESTAMPTZ NOT NULL,
    value_date DATE NOT NULL,
    amount_paise BIGINT NOT NULL,
    utr TEXT,
    narration TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR'
);

CREATE TABLE IF NOT EXISTS source_payout (
    payout_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    created_at TIMESTAMPTZ NOT NULL,
    settled_at TIMESTAMPTZ,
    amount_paise BIGINT NOT NULL,
    fee_paise BIGINT NOT NULL DEFAULT 0,
    tax_paise BIGINT NOT NULL DEFAULT 0,
    utr TEXT,
    status TEXT NOT NULL CHECK (status IN ('processed', 'reversed', 'failed')),
    currency TEXT NOT NULL DEFAULT 'INR'
);

CREATE TABLE IF NOT EXISTS source_ledger (
    ledger_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    journal_id TEXT NOT NULL,
    entry_date DATE NOT NULL,
    amount_paise BIGINT NOT NULL,
    account TEXT NOT NULL
        CHECK (account IN ('bank', 'settlements_receivable', 'gateway_fees', 'gateway_tax')),
    reference TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR'
);

CREATE TABLE IF NOT EXISTS truth_groups (
    group_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    kind TEXT NOT NULL,
    cohort TEXT NOT NULL,
    bank_ids JSONB NOT NULL DEFAULT '[]',
    payout_ids JSONB NOT NULL DEFAULT '[]',
    ledger_ids JSONB NOT NULL DEFAULT '[]',
    expected_outcome TEXT NOT NULL CHECK (expected_outcome IN ('resolved', 'unresolved')),
    expected_tag TEXT,
    expected_bucket TEXT
);

CREATE TABLE IF NOT EXISTS match_groups (
    group_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    kind TEXT NOT NULL,
    bank_ids JSONB NOT NULL DEFAULT '[]',
    payout_ids JSONB NOT NULL DEFAULT '[]',
    ledger_ids JSONB NOT NULL DEFAULT '[]',
    confidence DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('deterministic', 'agent')),
    fields_matched JSONB NOT NULL DEFAULT '[]',
    tolerances_used JSONB NOT NULL DEFAULT '[]',
    tag TEXT NOT NULL,
    reason TEXT NOT NULL,
    agent_turns INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS link_decisions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    link_type TEXT NOT NULL CHECK (link_type IN ('bank_payout', 'payout_ledger')),
    left_id TEXT NOT NULL,
    right_id TEXT NOT NULL,
    predicted BOOLEAN NOT NULL,
    truth BOOLEAN NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('TP', 'FP', 'FN', 'TN'))
);

CREATE TABLE IF NOT EXISTS exceptions (
    exception_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    row_ids JSONB NOT NULL DEFAULT '[]',
    bucket TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    evidence JSONB NOT NULL DEFAULT '[]',
    proposed_action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'assigned', 'resolved', 'wont_fix')),
    assignee TEXT,
    resolution_note TEXT
);

CREATE TABLE IF NOT EXISTS agent_calls (
    call_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    seq INTEGER NOT NULL,
    turns INTEGER NOT NULL,
    tools_used JSONB NOT NULL DEFAULT '[]',
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    cost_usd DOUBLE PRECISION NOT NULL,
    latency_ms INTEGER NOT NULL,
    prompt_redacted JSONB NOT NULL,
    response JSONB NOT NULL,
    guardrail_verdict TEXT NOT NULL CHECK (guardrail_verdict IN ('accepted', 'rejected')),
    guardrail_reasons JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS closures (
    closure_id TEXT PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    target TEXT NOT NULL,
    action TEXT NOT NULL
        CHECK (action IN ('mark_reconciled', 'post_adjustment', 'open_exception')),
    before JSONB NOT NULL,
    after JSONB NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reversed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS eval_sweeps (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    sweep_type TEXT NOT NULL,
    seed INTEGER NOT NULL,
    seed_set TEXT NOT NULL,
    report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS control_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    control_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS run_requests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    config JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'claimed', 'complete', 'failed')),
    claimed_by TEXT,
    claimed_at TIMESTAMPTZ,
    result_run_id UUID REFERENCES runs(run_id),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_source_bank_run ON source_bank(run_id);
CREATE INDEX IF NOT EXISTS idx_source_payout_run ON source_payout(run_id);
CREATE INDEX IF NOT EXISTS idx_source_ledger_run ON source_ledger(run_id);
CREATE INDEX IF NOT EXISTS idx_truth_groups_run ON truth_groups(run_id);
CREATE INDEX IF NOT EXISTS idx_match_groups_run ON match_groups(run_id);
CREATE INDEX IF NOT EXISTS idx_link_decisions_run ON link_decisions(run_id);
CREATE INDEX IF NOT EXISTS idx_exceptions_run ON exceptions(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_calls_run ON agent_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_closures_run ON closures(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_sweeps_run ON eval_sweeps(run_id);
CREATE INDEX IF NOT EXISTS idx_control_results_run ON control_results(run_id);
CREATE INDEX IF NOT EXISTS idx_run_requests_status ON run_requests(status);
CREATE INDEX IF NOT EXISTS idx_run_requests_result_run ON run_requests(result_run_id);

-- ============================================================
-- Row Level Security (§5.2)
-- ============================================================

ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_payout ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE truth_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE link_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE exceptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE closures ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_sweeps ENABLE ROW LEVEL SECURITY;
ALTER TABLE control_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE run_requests ENABLE ROW LEVEL SECURITY;

-- Idempotency note: CREATE POLICY has no "IF NOT EXISTS" clause in
-- PostgreSQL (unlike CREATE TABLE/CREATE INDEX). Every policy below is
-- DROP POLICY IF EXISTS + plain CREATE POLICY, which is genuinely idempotent
-- and re-applies clean. (P0 review fix — the earlier single-statement form
-- combining CREATE POLICY with a not-exists guard is invalid syntax and
-- would abort the whole migration transaction on first apply.)

-- anon: SELECT only on read-safe tables. closures is deliberately NOT exposed
-- here — it holds write-back before/after state and is service_role-only,
-- same category as run_requests (§5.2 role table).
DROP POLICY IF EXISTS anon_select_runs ON runs;
CREATE POLICY anon_select_runs ON runs FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_source_bank ON source_bank;
CREATE POLICY anon_select_source_bank ON source_bank FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_source_payout ON source_payout;
CREATE POLICY anon_select_source_payout ON source_payout FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_source_ledger ON source_ledger;
CREATE POLICY anon_select_source_ledger ON source_ledger FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_truth_groups ON truth_groups;
CREATE POLICY anon_select_truth_groups ON truth_groups FOR SELECT TO anon
    USING ((SELECT status FROM runs WHERE runs.run_id = truth_groups.run_id) = 'complete');
DROP POLICY IF EXISTS anon_select_match_groups ON match_groups;
CREATE POLICY anon_select_match_groups ON match_groups FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_link_decisions ON link_decisions;
CREATE POLICY anon_select_link_decisions ON link_decisions FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_exceptions ON exceptions;
CREATE POLICY anon_select_exceptions ON exceptions FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_agent_calls ON agent_calls;
CREATE POLICY anon_select_agent_calls ON agent_calls FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_eval_sweeps ON eval_sweeps;
CREATE POLICY anon_select_eval_sweeps ON eval_sweeps FOR SELECT TO anon USING (true);
DROP POLICY IF EXISTS anon_select_control_results ON control_results;
CREATE POLICY anon_select_control_results ON control_results FOR SELECT TO anon USING (true);

-- authenticated: same read set as anon (still no closures), plus INSERT
-- run_requests, plus UPDATE on exceptions restricted to triage columns only
-- (status/assignee/resolution_note) via column-level GRANT below — RLS
-- USING/WITH CHECK is row-scoped, it cannot restrict which columns change,
-- so bucket/evidence/severity stay immutable to a non-service caller.
DROP POLICY IF EXISTS auth_select_runs ON runs;
CREATE POLICY auth_select_runs ON runs FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_source_bank ON source_bank;
CREATE POLICY auth_select_source_bank ON source_bank FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_source_payout ON source_payout;
CREATE POLICY auth_select_source_payout ON source_payout FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_source_ledger ON source_ledger;
CREATE POLICY auth_select_source_ledger ON source_ledger FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_truth_groups ON truth_groups;
CREATE POLICY auth_select_truth_groups ON truth_groups FOR SELECT TO authenticated
    USING ((SELECT status FROM runs WHERE runs.run_id = truth_groups.run_id) = 'complete');
DROP POLICY IF EXISTS auth_select_match_groups ON match_groups;
CREATE POLICY auth_select_match_groups ON match_groups FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_link_decisions ON link_decisions;
CREATE POLICY auth_select_link_decisions ON link_decisions FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_exceptions ON exceptions;
CREATE POLICY auth_select_exceptions ON exceptions FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_agent_calls ON agent_calls;
CREATE POLICY auth_select_agent_calls ON agent_calls FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_eval_sweeps ON eval_sweeps;
CREATE POLICY auth_select_eval_sweeps ON eval_sweeps FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_select_control_results ON control_results;
CREATE POLICY auth_select_control_results ON control_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS auth_select_run_requests ON run_requests;
CREATE POLICY auth_select_run_requests ON run_requests FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS auth_insert_run_requests ON run_requests;
CREATE POLICY auth_insert_run_requests ON run_requests FOR INSERT TO authenticated
    WITH CHECK (true);

DROP POLICY IF EXISTS auth_update_exceptions ON exceptions;
CREATE POLICY auth_update_exceptions ON exceptions FOR UPDATE TO authenticated
    USING (true) WITH CHECK (true);
-- Row-level policy above allows the UPDATE to reach any row; column-level
-- grant below is what actually confines which columns authenticated can
-- change. Revoke the broad table-level UPDATE first so nothing but the
-- three triage columns is writable.
REVOKE UPDATE ON exceptions FROM authenticated;
GRANT UPDATE (status, assignee, resolution_note) ON exceptions TO authenticated;

-- service_role: full access (worker only, never in browser)
DROP POLICY IF EXISTS service_all_runs ON runs;
CREATE POLICY service_all_runs ON runs FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_source_bank ON source_bank;
CREATE POLICY service_all_source_bank ON source_bank FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_source_payout ON source_payout;
CREATE POLICY service_all_source_payout ON source_payout FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_source_ledger ON source_ledger;
CREATE POLICY service_all_source_ledger ON source_ledger FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_truth_groups ON truth_groups;
CREATE POLICY service_all_truth_groups ON truth_groups FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_match_groups ON match_groups;
CREATE POLICY service_all_match_groups ON match_groups FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_link_decisions ON link_decisions;
CREATE POLICY service_all_link_decisions ON link_decisions FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_exceptions ON exceptions;
CREATE POLICY service_all_exceptions ON exceptions FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_agent_calls ON agent_calls;
CREATE POLICY service_all_agent_calls ON agent_calls FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_closures ON closures;
CREATE POLICY service_all_closures ON closures FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_eval_sweeps ON eval_sweeps;
CREATE POLICY service_all_eval_sweeps ON eval_sweeps FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_control_results ON control_results;
CREATE POLICY service_all_control_results ON control_results FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_all_run_requests ON run_requests;
CREATE POLICY service_all_run_requests ON run_requests FOR ALL TO service_role USING (true) WITH CHECK (true);

-- anon has NO write path on any table (verified by check 0.7 / 6.6)

-- ============================================================
-- Realtime (P11 Eval Lab: live status on submitted run_requests)
-- ============================================================
-- supabase_realtime publishes no tables by default. Without this, a
-- postgres_changes subscription on run_requests connects but never
-- fires. Realtime respects RLS, so an unauthenticated session still
-- receives nothing -- this does not widen the SELECT policy above it.
ALTER TABLE public.run_requests REPLICA IDENTITY FULL;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'run_requests'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.run_requests;
    END IF;
END $$;
