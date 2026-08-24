import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";
import { SEED_RANGE_SUMMARY, SEED_SETS, resolveSeedSet } from "@/lib/seed-protocol";
import type { Config, SeedSet } from "@/types/report";

/** The four modes are exactly Config["mode"] — never a widened string list. */
export const RUN_MODES: readonly Config["mode"][] = [
  "rules_only",
  "agent_only",
  "rules_agent",
  "random",
];

export const N_MIN = 1;
export const N_MAX = 100_000;

export interface RunRequestConfig {
  seed: number;
  n: number;
  mode: Config["mode"];
}

export interface RunRequestRow {
  id: number;
  config: RunRequestConfig | null;
  status: string;
  claimed_by: string | null;
  claimed_at: string | null;
  result_run_id: string | null;
  error_message: string | null;
  created_at: string;
}

const REQUEST_COLUMNS =
  "id, config, status, claimed_by, claimed_at, result_run_id, error_message, created_at";

const sel = (s: string): string => s;

export interface RequestFormValues {
  seed: string;
  n: string;
  mode: Config["mode"];
}

export interface RequestValidation {
  seedSet: SeedSet | null;
  errors: { seed?: string; n?: string; mode?: string };
  valid: boolean;
  parsed: RunRequestConfig | null;
}

/** Validation against the seed protocol and the Config contract. */
export function validateRequest(values: RequestFormValues): RequestValidation {
  const errors: RequestValidation["errors"] = {};

  const seed = Number(values.seed);
  const seedIsInt = values.seed.trim() !== "" && Number.isInteger(seed);
  const seedSet = seedIsInt ? resolveSeedSet(seed) : null;
  if (!seedIsInt) errors.seed = "Seed must be an integer.";
  else if (seedSet === null)
    errors.seed = `Seed ${seed} is outside every declared set — ${SEED_RANGE_SUMMARY}.`;

  const n = Number(values.n);
  const nIsInt = values.n.trim() !== "" && Number.isInteger(n);
  if (!nIsInt) errors.n = "n must be an integer.";
  else if (n < N_MIN || n > N_MAX) errors.n = `n must be between ${N_MIN} and ${N_MAX}.`;

  if (!RUN_MODES.includes(values.mode)) errors.mode = "Mode must be one of the four arms.";

  const valid = Object.keys(errors).length === 0;
  return {
    seedSet,
    errors,
    valid,
    parsed: valid ? { seed, n, mode: values.mode } : null,
  };
}

export function seedSetNote(seedSet: SeedSet | null): string | null {
  return seedSet
    ? `${SEED_SETS[seedSet].label} set (${SEED_SETS[seedSet].range}) — ${SEED_SETS[seedSet].claimNote}`
    : null;
}

async function fetchRunRequests(ids: readonly number[]): Promise<RunRequestRow[]> {
  const { data, error } = await supabase
    .from("run_requests")
    .select(sel(REQUEST_COLUMNS))
    .in("id", ids as number[])
    .order("created_at", { ascending: false })
    .returns<RunRequestRow[]>();

  if (error) throw new Error(error.message);
  return data ?? [];
}

/**
 * This session's own run requests. `run_requests` is readable by every
 * authenticated user, so the panel is scoped client-side to the ids this
 * session inserted rather than showing everyone's queue.
 */
export function useRunRequests(enabled: boolean) {
  const queryClient = useQueryClient();
  const [ids, setIds] = useState<number[]>([]);
  const [live, setLive] = useState(false);
  const idsRef = useRef<number[]>([]);
  idsRef.current = ids;

  const key = useMemo(
    () => ["run-requests", [...ids].sort((a, b) => a - b).join(",")] as const,
    [ids],
  );

  const query = useQuery({
    queryKey: key,
    queryFn: () => fetchRunRequests(idsRef.current),
    enabled: isBackendConfigured() && enabled && ids.length > 0,
    // Polling fallback while the realtime socket is not subscribed.
    refetchInterval: live ? false : 5_000,
  });

  const insert = useMutation({
    mutationFn: async (config: RunRequestConfig): Promise<RunRequestRow> => {
      const { data, error } = await supabase
        .from("run_requests")
        .insert({ config } as never)
        .select(sel(REQUEST_COLUMNS))
        .single()
        .returns<RunRequestRow>();

      if (error) throw new Error(error.message);
      return data;
    },
    onSuccess: (row) => {
      setIds((current) => (current.includes(row.id) ? current : [...current, row.id]));
      queryClient.setQueryData<RunRequestRow[]>(key, (current) => [row, ...(current ?? [])]);
    },
  });

  useEffect(() => {
    if (!isBackendConfigured() || !enabled || ids.length === 0) {
      setLive(false);
      return;
    }

    const filter = `id=in.(${[...ids].sort((a, b) => a - b).join(",")})`;

    const channel = supabase
      .channel(`run-requests-${ids.length}-${ids[ids.length - 1]}`)
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "run_requests", filter },
        () => void queryClient.invalidateQueries({ queryKey: key }),
      )
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "run_requests", filter },
        (payload) => {
          const next = payload.new as RunRequestRow;
          queryClient.setQueryData<RunRequestRow[]>(key, (current) =>
            (current ?? []).map((row) => (row.id === next.id ? { ...row, ...next } : row)),
          );
        },
      )
      .subscribe((status) => {
        const subscribed = status === "SUBSCRIBED";
        setLive(subscribed);
        // Refetch once on subscribe / resubscribe so no transition is missed
        // while the socket was down.
        if (subscribed) void queryClient.invalidateQueries({ queryKey: key });
      });

    return () => {
      setLive(false);
      void supabase.removeChannel(channel);
    };
  }, [enabled, ids, key, queryClient]);

  return { query, insert, ids, live };
}
