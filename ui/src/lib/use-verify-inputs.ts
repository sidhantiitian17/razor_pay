import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";

/** The six negative controls, exactly as the engine names them. */
export const CONTROL_NAMES = [
  "shuffled_truth",
  "null_agent",
  "random_matcher",
  "poisoned_prompt",
  "inverted_rule",
  "disabled_dedup",
] as const;

export type ControlName = (typeof CONTROL_NAMES)[number];

export interface ControlResultRow {
  run_id: string;
  control_name: string;
  passed: boolean;
  details: unknown;
  created_at: string;
}

const CONTROL_COLUMNS = "run_id, control_name, passed, details, created_at";

const sel = (s: string): string => s;

async function fetchControlResults(runId: string): Promise<ControlResultRow[]> {
  const { data, error } = await supabase
    .from("control_results")
    .select(sel(CONTROL_COLUMNS))
    .eq("run_id", runId)
    .order("created_at", { ascending: true })
    .returns<ControlResultRow[]>();

  if (error) throw new Error(error.message);
  return data ?? [];
}

export function useControlResults(runId: string | undefined) {
  return useQuery({
    queryKey: ["control-results", runId ?? "none"] as const,
    queryFn: () => fetchControlResults(runId as string),
    enabled: isBackendConfigured() && Boolean(runId),
    staleTime: 15_000,
  });
}

export interface ClosureRow {
  closure_id: string;
  run_id: string;
  target: string;
  action: string;
  applied_at: string;
  reversed_at: string | null;
}

const CLOSURE_COLUMNS = "closure_id, run_id, target, action, applied_at, reversed_at";

async function fetchClosures(runId: string): Promise<ClosureRow[]> {
  const { data, error } = await supabase
    .from("closures")
    .select(sel(CLOSURE_COLUMNS))
    .eq("run_id", runId)
    .order("applied_at", { ascending: true })
    .returns<ClosureRow[]>();

  if (error) throw new Error(error.message);
  return data ?? [];
}

export function useClosures(runId: string | undefined) {
  return useQuery({
    queryKey: ["closures", runId ?? "none"] as const,
    queryFn: () => fetchClosures(runId as string),
    enabled: isBackendConfigured() && Boolean(runId),
    staleTime: 15_000,
  });
}
