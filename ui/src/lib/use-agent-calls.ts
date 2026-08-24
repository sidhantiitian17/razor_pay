import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";

/**
 * One agent call, as written by the engine. `tools_used` / `guardrail_reasons`
 * arrive as jsonb arrays and are narrowed to string arrays; `prompt_redacted`
 * and `response` are kept verbatim as unknown JSON and rendered as-is.
 */
export interface AgentCallRow {
  call_id: string;
  run_id: string;
  seq: number;
  turns: number;
  tools_used: string[];
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  prompt_redacted: unknown;
  response: unknown;
  guardrail_verdict: string;
  guardrail_reasons: string[];
}

interface RawAgentCallRow {
  call_id: string;
  run_id: string;
  seq: number;
  turns: number;
  tools_used: unknown;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  prompt_redacted: unknown;
  response: unknown;
  guardrail_verdict: string;
  guardrail_reasons: unknown;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((entry) => (typeof entry === "string" ? entry : JSON.stringify(entry)));
}

const COLUMNS =
  "call_id, run_id, seq, turns, tools_used, tokens_in, tokens_out, cost_usd, latency_ms, prompt_redacted, response, guardrail_verdict, guardrail_reasons";

const sel = (s: string): string => s;

async function fetchAgentCalls(runId: string): Promise<AgentCallRow[]> {
  const { data, error } = await supabase
    .from("agent_calls")
    .select(sel(COLUMNS))
    .eq("run_id", runId)
    .order("seq", { ascending: true })
    .returns<RawAgentCallRow[]>();

  if (error) throw new Error(error.message);

  return (data ?? []).map((row) => ({
    call_id: row.call_id,
    run_id: row.run_id,
    seq: row.seq,
    turns: row.turns,
    tools_used: toStringArray(row.tools_used),
    tokens_in: row.tokens_in,
    tokens_out: row.tokens_out,
    cost_usd: row.cost_usd,
    latency_ms: row.latency_ms,
    prompt_redacted: row.prompt_redacted,
    response: row.response,
    guardrail_verdict: row.guardrail_verdict,
    guardrail_reasons: toStringArray(row.guardrail_reasons),
  }));
}

export function useAgentCalls(runId: string | undefined) {
  return useQuery({
    queryKey: ["agent-calls", runId ?? "none"] as const,
    queryFn: () => fetchAgentCalls(runId as string),
    enabled: isBackendConfigured() && Boolean(runId),
    staleTime: 15_000,
  });
}

export interface AgentCallTotals {
  calls: number;
  turns: number;
  tokensIn: number;
  tokensOut: number;
  costUsd: number;
  accepted: number;
  rejected: number;
  reasonCounts: Record<string, number>;
}

/** Totals summed from the fetched rows — never taken from the report. */
export function totalAgentCalls(rows: AgentCallRow[]): AgentCallTotals {
  const reasonCounts: Record<string, number> = {};
  let accepted = 0;
  let rejected = 0;

  for (const row of rows) {
    if (row.guardrail_verdict === "accepted") accepted += 1;
    else if (row.guardrail_verdict === "rejected") rejected += 1;
    for (const reason of row.guardrail_reasons) {
      reasonCounts[reason] = (reasonCounts[reason] ?? 0) + 1;
    }
  }

  return {
    calls: rows.length,
    turns: rows.reduce((sum, row) => sum + row.turns, 0),
    tokensIn: rows.reduce((sum, row) => sum + row.tokens_in, 0),
    tokensOut: rows.reduce((sum, row) => sum + row.tokens_out, 0),
    costUsd: rows.reduce((sum, row) => sum + row.cost_usd, 0),
    accepted,
    rejected,
    reasonCounts,
  };
}
