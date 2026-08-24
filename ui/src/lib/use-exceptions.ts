import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";

/** The nine unresolved buckets, exactly as the engine writes them. */
export const BUCKETS = [
  "amount_mismatch",
  "fee_mismatch",
  "timing_break",
  "missing_utr",
  "duplicate",
  "refund_unpaired",
  "orphan_bank",
  "orphan_ledger",
  "partial_group",
] as const;

export type Bucket = (typeof BUCKETS)[number];

export const SEVERITIES = ["low", "medium", "high"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const STATUSES = ["open", "assigned", "resolved", "wont_fix"] as const;
export type TriageStatus = (typeof STATUSES)[number];

/** Unresolved side of the workqueue — the statuses still requiring a decision. */
export const UNRESOLVED_STATUSES: readonly string[] = ["open", "assigned"];

/**
 * One exception row. `row_ids` and `evidence` arrive as jsonb and are narrowed
 * to string arrays here; nothing else is widened.
 */
export interface ExceptionRow {
  exception_id: string;
  run_id: string;
  row_ids: string[];
  bucket: string;
  severity: string;
  evidence: string[];
  proposed_action: string;
  status: string;
  assignee: string | null;
  resolution_note: string | null;
}

interface RawExceptionRow {
  exception_id: string;
  run_id: string;
  row_ids: unknown;
  bucket: string;
  severity: string;
  evidence: unknown;
  proposed_action: string;
  status: string;
  assignee: string | null;
  resolution_note: string | null;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === "string");
}

const COLUMNS =
  "exception_id, run_id, row_ids, bucket, severity, evidence, proposed_action, status, assignee, resolution_note";

const sel = (s: string): string => s;

async function fetchExceptions(runId: string): Promise<ExceptionRow[]> {
  const { data, error } = await supabase
    .from("exceptions")
    .select(sel(COLUMNS))
    .eq("run_id", runId)
    .order("severity", { ascending: true })
    .returns<RawExceptionRow[]>();

  if (error) throw new Error(error.message);

  return (data ?? []).map((row) => ({
    exception_id: row.exception_id,
    run_id: row.run_id,
    row_ids: toStringArray(row.row_ids),
    bucket: row.bucket,
    severity: row.severity,
    evidence: toStringArray(row.evidence),
    proposed_action: row.proposed_action,
    status: row.status,
    assignee: row.assignee,
    resolution_note: row.resolution_note,
  }));
}

export function exceptionsQueryKey(runId: string | undefined) {
  return ["exceptions", runId ?? "none"] as const;
}

export function useExceptions(runId: string | undefined) {
  return useQuery({
    queryKey: exceptionsQueryKey(runId),
    queryFn: () => fetchExceptions(runId as string),
    enabled: isBackendConfigured() && Boolean(runId),
    staleTime: 15_000,
  });
}
