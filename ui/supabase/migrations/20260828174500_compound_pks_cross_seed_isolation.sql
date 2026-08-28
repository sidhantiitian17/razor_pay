-- Migration: compound primary keys for cross-seed isolation
-- Fixes: single-column PKs on source/group/exception/call/closure tables caused
-- upsert to collide across seed runs (generator counters reset per generate_dataset()).
-- Mirrors the SQLite adapter pattern: PRIMARY KEY (run_id, entity_id).
--
-- Affected tables: source_bank, source_payout, source_ledger,
--                  truth_groups, match_groups, exceptions, agent_calls, closures.
-- Unaffected tables (already safe): runs (UUID PK), link_decisions (BIGINT IDENTITY),
--                  eval_sweeps (BIGINT IDENTITY), control_results (BIGINT IDENTITY),
--                  run_requests (BIGINT IDENTITY).
--
-- Strategy per table:
--   1. DROP the old single-column PRIMARY KEY constraint.
--   2. ADD a compound PRIMARY KEY (run_id, entity_id).
-- Idempotent: wrapped in DO $$ BEGIN … EXCEPTION WHEN … END $$ blocks.

-- ─── source_bank ───────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE source_bank DROP CONSTRAINT IF EXISTS source_bank_pkey;
    ALTER TABLE source_bank ADD PRIMARY KEY (run_id, bank_id);
EXCEPTION WHEN others THEN
    -- If pkey already has compound form, this is a no-op.
    RAISE NOTICE 'source_bank PK already migrated or error: %', SQLERRM;
END $$;

-- ─── source_payout ─────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE source_payout DROP CONSTRAINT IF EXISTS source_payout_pkey;
    ALTER TABLE source_payout ADD PRIMARY KEY (run_id, payout_id);
EXCEPTION WHEN others THEN
    RAISE NOTICE 'source_payout PK already migrated or error: %', SQLERRM;
END $$;

-- ─── source_ledger ─────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE source_ledger DROP CONSTRAINT IF EXISTS source_ledger_pkey;
    ALTER TABLE source_ledger ADD PRIMARY KEY (run_id, ledger_id);
EXCEPTION WHEN others THEN
    RAISE NOTICE 'source_ledger PK already migrated or error: %', SQLERRM;
END $$;

-- ─── truth_groups ──────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE truth_groups DROP CONSTRAINT IF EXISTS truth_groups_pkey;
    ALTER TABLE truth_groups ADD PRIMARY KEY (run_id, group_id);
EXCEPTION WHEN others THEN
    RAISE NOTICE 'truth_groups PK already migrated or error: %', SQLERRM;
END $$;

-- ─── match_groups ──────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE match_groups DROP CONSTRAINT IF EXISTS match_groups_pkey;
    ALTER TABLE match_groups ADD PRIMARY KEY (run_id, group_id);
EXCEPTION WHEN others THEN
    RAISE NOTICE 'match_groups PK already migrated or error: %', SQLERRM;
END $$;

-- ─── exceptions ────────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE exceptions DROP CONSTRAINT IF EXISTS exceptions_pkey;
    ALTER TABLE exceptions ADD PRIMARY KEY (run_id, exception_id);
EXCEPTION WHEN others THEN
    RAISE NOTICE 'exceptions PK already migrated or error: %', SQLERRM;
END $$;

-- ─── agent_calls ───────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE agent_calls DROP CONSTRAINT IF EXISTS agent_calls_pkey;
    ALTER TABLE agent_calls ADD PRIMARY KEY (run_id, call_id);
EXCEPTION WHEN others THEN
    RAISE NOTICE 'agent_calls PK already migrated or error: %', SQLERRM;
END $$;

-- ─── closures ──────────────────────────────────────────────────────────────────
DO $$ BEGIN
    ALTER TABLE closures DROP CONSTRAINT IF EXISTS closures_pkey;
    ALTER TABLE closures ADD PRIMARY KEY (run_id, closure_id);
EXCEPTION WHEN others THEN
    RAISE NOTICE 'closures PK already migrated or error: %', SQLERRM;
END $$;
