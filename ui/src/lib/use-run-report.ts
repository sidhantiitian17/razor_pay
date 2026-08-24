import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";
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

async function fetchLatestRunReport(): Promise<RunReportRow | null> {
  const { data, error } = await supabase
    .from("runs")
    .select(sel("run_id, engine_version, status, created_at, completed_at, report"))
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle()
    .returns<RunReportRow | null>();

  if (error) throw new Error(error.message);
  return data;
}

export function useRunReport() {
  return useQuery({
    queryKey: ["run-report", "latest"],
    queryFn: fetchLatestRunReport,
    enabled: isBackendConfigured(),
    staleTime: 30_000,
  });
}
