import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { formatCount, formatPaise } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  compareSources,
  useExceptionSources,
  type ExceptionSources,
} from "@/lib/use-exception-sources";
import type { ExceptionRow } from "@/lib/use-exceptions";
import type { TriageAction } from "@/lib/use-triage";
import { TriageActions } from "./triage-actions";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border/50 py-1">
      <span className="label-micro">{label}</span>
      <span className="tnum text-xs text-foreground">{value}</span>
    </div>
  );
}

function SourceColumn({
  title,
  present,
  children,
}: {
  title: string;
  present: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="panel p-3">
      <div className="mb-2 text-xs font-semibold text-foreground">{title}</div>
      {present ? (
        children
      ) : (
        <p className="text-xs text-muted-foreground">Not referenced by this exception.</p>
      )}
    </div>
  );
}

function SourcePanels({ sources }: { sources: ExceptionSources }) {
  const bank = sources.bank[0];
  const payout = sources.payout[0];
  const ledger = sources.ledger[0];

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <SourceColumn title="Bank" present={Boolean(bank)}>
        {bank ? (
          <div>
            <Row label="bank_id" value={bank.bank_id} />
            <Row label="posted_at" value={bank.posted_at} />
            <Row label="value_date" value={bank.value_date} />
            <Row label="amount" value={formatPaise(bank.amount_paise)} />
            <Row label="utr" value={bank.utr ?? "—"} />
            <Row label="currency" value={bank.currency} />
            <Row label="narration" value={bank.narration} />
          </div>
        ) : null}
      </SourceColumn>

      <SourceColumn title="Gateway payout" present={Boolean(payout)}>
        {payout ? (
          <div>
            <Row label="payout_id" value={payout.payout_id} />
            <Row label="created_at" value={payout.created_at} />
            <Row label="settled_at" value={payout.settled_at ?? "—"} />
            <Row label="amount" value={formatPaise(payout.amount_paise)} />
            <Row label="fee" value={formatPaise(payout.fee_paise)} />
            <Row label="tax" value={formatPaise(payout.tax_paise)} />
            <Row label="utr" value={payout.utr ?? "—"} />
            <Row label="status" value={payout.status} />
            <Row label="currency" value={payout.currency} />
          </div>
        ) : null}
      </SourceColumn>

      <SourceColumn title="Ledger" present={Boolean(ledger)}>
        {ledger ? (
          <div>
            <Row label="ledger_id" value={ledger.ledger_id} />
            <Row label="journal_id" value={ledger.journal_id} />
            <Row label="entry_date" value={ledger.entry_date} />
            <Row label="amount" value={formatPaise(ledger.amount_paise)} />
            <Row label="account" value={ledger.account} />
            <Row label="reference" value={ledger.reference} />
            <Row label="currency" value={ledger.currency} />
          </div>
        ) : null}
      </SourceColumn>
    </div>
  );
}

export function ExceptionSheet({
  exception,
  runId,
  assigneeLabel,
  pending,
  onAction,
  onClose,
}: {
  exception: ExceptionRow | null;
  runId: string | undefined;
  assigneeLabel: string | null;
  pending: boolean;
  onAction: (action: TriageAction) => void;
  onClose: () => void;
}) {
  const sources = useExceptionSources(runId, exception?.row_ids);
  const comparisons = sources.data ? compareSources(sources.data) : [];
  const matched = comparisons.filter((c) => c.matched);
  const unmatched = comparisons.filter((c) => !c.matched);

  return (
    <Sheet open={Boolean(exception)} onOpenChange={(open) => (open ? undefined : onClose())}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-3xl">
        {exception ? (
          <>
            <SheetHeader>
              <SheetTitle className="tnum text-base">{exception.exception_id}</SheetTitle>
              <SheetDescription>
                bucket {exception.bucket} · severity {exception.severity} · status{" "}
                {exception.status} · {formatCount(exception.row_ids.length)} source rows
              </SheetDescription>
            </SheetHeader>

            <div className="mt-4 grid gap-3">
              {sources.isPending && exception.row_ids.length > 0 ? (
                <p className="text-xs text-muted-foreground">Loading source records…</p>
              ) : sources.isError ? (
                <p role="alert" className="text-xs text-destructive">
                  Source records unavailable: {(sources.error as Error).message}
                </p>
              ) : sources.data ? (
                <SourcePanels sources={sources.data} />
              ) : null}

              {sources.data && sources.data.unknownIds.length > 0 ? (
                <div className="panel p-3 text-xs text-muted-foreground">
                  Unrecognised source IDs (no known prefix):{" "}
                  <span className="tnum">{sources.data.unknownIds.join(", ")}</span>
                </div>
              ) : null}

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="panel p-3">
                  <div className="label-micro">Fields matched</div>
                  {matched.length === 0 ? (
                    <p className="mt-1 text-xs text-muted-foreground">None.</p>
                  ) : (
                    <ul className="mt-1 grid gap-1">
                      {matched.map((c) => (
                        <li key={c.field} className="text-xs text-matched">
                          {c.field}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="panel border-unresolved/50 p-3">
                  <div className="label-micro">Fields not matched</div>
                  {unmatched.length === 0 ? (
                    <p className="mt-1 text-xs text-muted-foreground">None.</p>
                  ) : (
                    <ul className="mt-1 grid gap-2">
                      {unmatched.map((c) => (
                        <li key={c.field} className="text-xs">
                          <div className="font-medium text-foreground">{c.field}</div>
                          <div className="tnum text-[11px] text-muted-foreground">
                            {c.observations
                              .filter((o) => o.value !== null && o.value !== "")
                              .map((o) => {
                                const rendered =
                                  c.kind === "paise"
                                    ? formatPaise(Number(o.value))
                                    : String(o.value);
                                return `${o.source}: ${rendered}`;
                              })
                              .join("  ·  ")}
                          </div>
                          {c.deltaLabel ? (
                            <div className={cn("tnum text-[11px] text-unresolved")}>
                              delta {c.deltaLabel}
                              {c.kind === "paise" && c.delta !== null
                                ? ` (${formatPaise(c.delta)})`
                                : ""}
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="panel p-3">
                <div className="label-micro">Evidence</div>
                {exception.evidence.length === 0 ? (
                  <p className="mt-1 text-xs text-muted-foreground">No evidence recorded.</p>
                ) : (
                  <ol className="mt-1 grid list-decimal gap-1 pl-4">
                    {exception.evidence.map((line, index) => (
                      <li key={index} className="text-xs text-foreground">
                        {line}
                      </li>
                    ))}
                  </ol>
                )}
              </div>

              <div className="panel p-3">
                <div className="label-micro">Proposed action</div>
                <p className="mt-1 text-xs text-foreground">{exception.proposed_action}</p>
                {exception.resolution_note ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Resolution note: {exception.resolution_note}
                  </p>
                ) : null}
              </div>

              <TriageActions assigneeLabel={assigneeLabel} pending={pending} onAction={onAction} />
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
