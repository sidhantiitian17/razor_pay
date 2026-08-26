DROP POLICY IF EXISTS anon_select_runs ON public.runs;
DROP POLICY IF EXISTS anon_select_exceptions ON public.exceptions;
DROP POLICY IF EXISTS anon_select_match_groups ON public.match_groups;
DROP POLICY IF EXISTS anon_select_link_decisions ON public.link_decisions;
DROP POLICY IF EXISTS anon_select_truth_groups ON public.truth_groups;
DROP POLICY IF EXISTS anon_select_agent_calls ON public.agent_calls;
DROP POLICY IF EXISTS anon_select_control_results ON public.control_results;
DROP POLICY IF EXISTS anon_select_eval_sweeps ON public.eval_sweeps;
DROP POLICY IF EXISTS anon_select_source_bank ON public.source_bank;
DROP POLICY IF EXISTS anon_select_source_payout ON public.source_payout;
DROP POLICY IF EXISTS anon_select_source_ledger ON public.source_ledger;

REVOKE SELECT ON public.runs, public.exceptions, public.match_groups, public.link_decisions,
  public.truth_groups, public.agent_calls, public.control_results, public.eval_sweeps,
  public.source_bank, public.source_payout, public.source_ledger, public.run_requests, public.closures
  FROM anon;

GRANT SELECT ON public.runs, public.exceptions, public.match_groups, public.link_decisions,
  public.truth_groups, public.agent_calls, public.control_results, public.eval_sweeps,
  public.source_bank, public.source_payout, public.source_ledger TO authenticated;