import { useQuery } from "@tanstack/react-query";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";

/**
 * `row_ids` carries no foreign key, so a source ID is routed to its table by
 * prefix only — never by guessing.
 */
export type SourceKind = "bank" | "payout" | "ledger" | "unknown";

export function classifySourceId(id: string): SourceKind {
  if (id.startsWith("BNK-")) return "bank";
  if (id.startsWith("pout_SYNTH")) return "payout";
  if (id.startsWith("LED-")) return "ledger";
  return "unknown";
}

export interface BankRecord {
  bank_id: string;
  posted_at: string;
  value_date: string;
  amount_paise: number;
  utr: string | null;
  narration: string;
  currency: string;
}

export interface PayoutRecord {
  payout_id: string;
  created_at: string;
  settled_at: string | null;
  amount_paise: number;
  fee_paise: number;
  tax_paise: number;
  utr: string | null;
  status: string;
  currency: string;
}

export interface LedgerRecord {
  ledger_id: string;
  journal_id: string;
  entry_date: string;
  amount_paise: number;
  account: string;
  reference: string;
  currency: string;
}

export interface ExceptionSources {
  bank: BankRecord[];
  payout: PayoutRecord[];
  ledger: LedgerRecord[];
  unknownIds: string[];
}

const sel = (s: string): string => s;

async function fetchSources(runId: string, rowIds: string[]): Promise<ExceptionSources> {
  const bankIds = rowIds.filter((id) => classifySourceId(id) === "bank");
  const payoutIds = rowIds.filter((id) => classifySourceId(id) === "payout");
  const ledgerIds = rowIds.filter((id) => classifySourceId(id) === "ledger");
  const unknownIds = rowIds.filter((id) => classifySourceId(id) === "unknown");

  const [bank, payout, ledger] = await Promise.all([
    bankIds.length
      ? supabase
          .from("source_bank")
          .select(sel("bank_id, posted_at, value_date, amount_paise, utr, narration, currency"))
          .eq("run_id", runId)
          .in("bank_id", bankIds)
          .returns<BankRecord[]>()
      : Promise.resolve({ data: [] as BankRecord[], error: null }),
    payoutIds.length
      ? supabase
          .from("source_payout")
          .select(
            sel(
              "payout_id, created_at, settled_at, amount_paise, fee_paise, tax_paise, utr, status, currency",
            ),
          )
          .eq("run_id", runId)
          .in("payout_id", payoutIds)
          .returns<PayoutRecord[]>()
      : Promise.resolve({ data: [] as PayoutRecord[], error: null }),
    ledgerIds.length
      ? supabase
          .from("source_ledger")
          .select(
            sel("ledger_id, journal_id, entry_date, amount_paise, account, reference, currency"),
          )
          .eq("run_id", runId)
          .in("ledger_id", ledgerIds)
          .returns<LedgerRecord[]>()
      : Promise.resolve({ data: [] as LedgerRecord[], error: null }),
  ]);

  const firstError = bank.error ?? payout.error ?? ledger.error;
  if (firstError) throw new Error(firstError.message);

  return {
    bank: bank.data ?? [],
    payout: payout.data ?? [],
    ledger: ledger.data ?? [],
    unknownIds,
  };
}

export function useExceptionSources(runId: string | undefined, rowIds: string[] | undefined) {
  const ids = rowIds ?? [];
  return useQuery({
    queryKey: ["exception-sources", runId ?? "none", ids.join("|")],
    queryFn: () => fetchSources(runId as string, ids),
    enabled: isBackendConfigured() && Boolean(runId) && ids.length > 0,
    staleTime: 60_000,
  });
}

/* ------------------------------------------------------------------ */
/* Field comparison — derived, never stored                            */
/* ------------------------------------------------------------------ */

export type FieldKind = "paise" | "date" | "text";

export interface FieldObservation {
  source: string;
  value: string | number | null;
}

export interface FieldComparison {
  field: string;
  kind: FieldKind;
  observations: FieldObservation[];
  matched: boolean;
  /** Paise delta for money fields, whole-day delta for dates. */
  delta: number | null;
  deltaLabel: string | null;
}

function dayIndex(value: string | null): number | null {
  if (!value) return null;
  const ms = Date.parse(value);
  if (Number.isNaN(ms)) return null;
  return Math.floor(ms / 86_400_000);
}

function build(
  field: string,
  kind: FieldKind,
  observations: FieldObservation[],
): FieldComparison | null {
  const present = observations.filter((o) => o.value !== null && o.value !== "");
  if (present.length < 2) return null;

  if (kind === "paise") {
    const numbers = present.map((o) => Number(o.value));
    const min = Math.min(...numbers);
    const max = Math.max(...numbers);
    const delta = max - min;
    return {
      field,
      kind,
      observations,
      matched: delta === 0,
      delta,
      deltaLabel: delta === 0 ? null : `${delta} paise spread`,
    };
  }

  if (kind === "date") {
    const days = present
      .map((o) => dayIndex(String(o.value)))
      .filter((d): d is number => d !== null);
    if (days.length < 2) return null;
    const delta = Math.max(...days) - Math.min(...days);
    return {
      field,
      kind,
      observations,
      matched: delta === 0,
      delta,
      deltaLabel: delta === 0 ? null : `${delta} day${delta === 1 ? "" : "s"} apart`,
    };
  }

  const values = new Set(present.map((o) => String(o.value)));
  return {
    field,
    kind,
    observations,
    matched: values.size === 1,
    delta: null,
    deltaLabel: values.size === 1 ? null : `${values.size} distinct values`,
  };
}

/**
 * Compares only the fields that exist on more than one of the records actually
 * referenced by this exception. Amounts stay integer paise here.
 */
export function compareSources(sources: ExceptionSources): FieldComparison[] {
  const bank = sources.bank[0];
  const payout = sources.payout[0];
  const ledger = sources.ledger[0];

  const comparisons: (FieldComparison | null)[] = [
    build("amount_paise", "paise", [
      { source: "bank", value: bank ? bank.amount_paise : null },
      { source: "payout", value: payout ? payout.amount_paise : null },
      { source: "ledger", value: ledger ? ledger.amount_paise : null },
    ]),
    build("net of fee + tax vs bank", "paise", [
      { source: "bank", value: bank ? bank.amount_paise : null },
      {
        source: "payout net",
        value: payout ? payout.amount_paise - payout.fee_paise - payout.tax_paise : null,
      },
    ]),
    build("utr", "text", [
      { source: "bank", value: bank ? bank.utr : null },
      { source: "payout", value: payout ? payout.utr : null },
    ]),
    build("currency", "text", [
      { source: "bank", value: bank ? bank.currency : null },
      { source: "payout", value: payout ? payout.currency : null },
      { source: "ledger", value: ledger ? ledger.currency : null },
    ]),
    build("settlement date", "date", [
      { source: "bank.value_date", value: bank ? bank.value_date : null },
      { source: "payout.settled_at", value: payout ? payout.settled_at : null },
      { source: "ledger.entry_date", value: ledger ? ledger.entry_date : null },
    ]),
  ];

  return comparisons.filter((c): c is FieldComparison => c !== null);
}
