-- 1. Role infrastructure
DO $$ BEGIN
  CREATE TYPE public.app_role AS ENUM ('admin', 'operator');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS public.user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role public.app_role NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, role)
);

GRANT SELECT ON public.user_roles TO authenticated;
GRANT ALL ON public.user_roles TO service_role;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS auth_select_own_roles ON public.user_roles;
CREATE POLICY auth_select_own_roles ON public.user_roles
  FOR SELECT TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS service_all_user_roles ON public.user_roles;
CREATE POLICY service_all_user_roles ON public.user_roles
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE OR REPLACE FUNCTION public.has_role(_user_id uuid, _role public.app_role)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  )
$$;

CREATE OR REPLACE FUNCTION public.is_recon_operator()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = auth.uid() AND role IN ('operator', 'admin')
  )
$$;

GRANT EXECUTE ON FUNCTION public.has_role(uuid, public.app_role) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.is_recon_operator() TO authenticated, service_role;

-- Backfill: Initial bootstrap for existing dev/test operator accounts.
-- In this development environment (dtgwbqcjblbcgclogvtv), existing auth.users rows correspond
-- strictly to provisioned CI/QA test operators. For new users, role assignment is NOT automatic;
-- new signups have zero table access until an administrator explicitly inserts an 'operator' or
-- 'admin' role into public.user_roles (enforced by RLS is_recon_operator() check).
INSERT INTO public.user_roles (user_id, role)
SELECT id, 'operator'::public.app_role FROM auth.users
ON CONFLICT (user_id, role) DO NOTHING;

-- 2. Restrict read access on reconciliation data to operators/admins
DROP POLICY IF EXISTS auth_select_runs ON public.runs;
CREATE POLICY auth_select_runs ON public.runs
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_source_bank ON public.source_bank;
CREATE POLICY auth_select_source_bank ON public.source_bank
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_source_ledger ON public.source_ledger;
CREATE POLICY auth_select_source_ledger ON public.source_ledger
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_source_payout ON public.source_payout;
CREATE POLICY auth_select_source_payout ON public.source_payout
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_match_groups ON public.match_groups;
CREATE POLICY auth_select_match_groups ON public.match_groups
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_link_decisions ON public.link_decisions;
CREATE POLICY auth_select_link_decisions ON public.link_decisions
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_exceptions ON public.exceptions;
CREATE POLICY auth_select_exceptions ON public.exceptions
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_agent_calls ON public.agent_calls;
CREATE POLICY auth_select_agent_calls ON public.agent_calls
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_control_results ON public.control_results;
CREATE POLICY auth_select_control_results ON public.control_results
  FOR SELECT TO authenticated USING (public.is_recon_operator());

DROP POLICY IF EXISTS auth_select_eval_sweeps ON public.eval_sweeps;
CREATE POLICY auth_select_eval_sweeps ON public.eval_sweeps
  FOR SELECT TO authenticated USING (public.is_recon_operator());

-- 3. Exception triage writes limited to operators/admins
DROP POLICY IF EXISTS auth_update_exceptions ON public.exceptions;
CREATE POLICY auth_update_exceptions ON public.exceptions
  FOR UPDATE TO authenticated
  USING (public.is_recon_operator())
  WITH CHECK (public.is_recon_operator());

-- 4. Ownership on run_requests
ALTER TABLE public.run_requests
  ADD COLUMN IF NOT EXISTS requested_by uuid DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE SET NULL;

DROP POLICY IF EXISTS auth_insert_run_requests ON public.run_requests;
CREATE POLICY auth_insert_run_requests ON public.run_requests
  FOR INSERT TO authenticated
  WITH CHECK (
    public.is_recon_operator()
    AND requested_by = auth.uid()
    AND status = 'pending'
    AND claimed_by IS NULL
    AND result_run_id IS NULL
    AND error_message IS NULL
  );

DROP POLICY IF EXISTS auth_select_run_requests ON public.run_requests;
CREATE POLICY auth_select_run_requests ON public.run_requests
  FOR SELECT TO authenticated
  USING (requested_by = auth.uid() OR public.has_role(auth.uid(), 'admin'));

-- 5. truth_groups: completed run AND operator/admin
DROP POLICY IF EXISTS auth_select_truth_groups ON public.truth_groups;
CREATE POLICY auth_select_truth_groups ON public.truth_groups
  FOR SELECT TO authenticated
  USING (
    public.is_recon_operator()
    AND (SELECT status FROM public.runs WHERE runs.run_id = truth_groups.run_id) = 'complete'
  );
