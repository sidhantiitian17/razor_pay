import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";
import { useCurrentRun } from "@/lib/current-run";
import type { ReconciliationReport } from "@/types/report";

/**
 * Selected run row. `report` is the frozen ReconciliationReport contract, or
 * null until the engine has written one. Read with the anon key under RLS.
 */
export interface RunReportRow {
  run_id: string;
  engine_version: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  report: ReconciliationReport | null;
}

const sel = (s: string): string => s;

const RUN_REPORT_COLUMNS = "run_id, engine_version, status, created_at, completed_at, report";

async function fetchRunReport(runId: string | null): Promise<RunReportRow | null> {
  let query = supabase.from("runs").select(sel(RUN_REPORT_COLUMNS));

  if (runId) query = query.eq("run_id", runId);
  else query = query.order("created_at", { ascending: false });

  const { data, error } = await query.limit(1).maybeSingle().returns<RunReportRow | null>();

  if (error) throw new Error(error.message);
  return data;
}

/**
 * The run the whole panel is pointed at: the header selection when there is
 * one, otherwise the newest run in the database.
 */
export function useRunReport() {
  const { selectedRunId } = useCurrentRun();

  return useQuery({
    queryKey: ["run-report", selectedRunId ?? "latest"] as const,
    queryFn: () => fetchRunReport(selectedRunId),
    enabled: isBackendConfigured(),
    staleTime: 30_000,
  });
}

/** Latest run for public/marketing surfaces; intentionally ignores header selection. */
export function useLatestRunReport(enabled = true) {
  return useQuery({
    queryKey: ["run-report", "latest-public"] as const,
    queryFn: () => fetchRunReport(null),
    enabled: enabled && isBackendConfigured(),
    staleTime: 30_000,
  });
}
