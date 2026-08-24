import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { CallSheet } from "@/components/trace/call-sheet";
import { CallTimeline } from "@/components/trace/call-timeline";
import { DataSurface, type SurfaceStatus } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";
import { totalAgentCalls, useAgentCalls, type AgentCallRow } from "@/lib/use-agent-calls";
import { useRunReport } from "@/lib/use-run-report";
import type { ReconciliationReport } from "@/types/report";

export const Route = createFileRoute("/agent-trace")({
  head: () => ({
    meta: [
      { title: "Agent Trace — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Ordered trace of every agent call in a reconciliation run: turns, tools, tokens, cost, latency and guardrail verdict, cross-checked against the run report.",
      },
      { property: "og:title", content: "Agent Trace — Settlement Reconciliation" },
      {
        property: "og:description",
        content:
          "Per-call agent trace with verbatim prompt and response, and per-call totals reconciled against the report's cost and guardrail figures.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: AgentTracePage,
});

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 6,
  maximumFractionDigits: 6,
});

function AgentTracePage() {
  const run = useRunReport();
  const runId = run.data?.run_id;
  const calls = useAgentCalls(runId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const rows = calls.data ?? [];
  const report = run.data?.report ?? null;

  const status: SurfaceStatus =
    run.isError || calls.isError
      ? "error"
      : run.isPending || (Boolean(runId) && calls.isPending)
        ? "loading"
        : rows.length === 0
          ? "empty"
          : "ready";

  const selected: AgentCallRow | null = rows.find((row) => row.call_id === selectedId) ?? null;

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Agent Trace"
          description="One row per agent call, ordered by seq. Per-call totals are summed from these rows and shown next to the report's own figures — a disagreement is displayed, not reconciled away."
        />
      </RevealItem>

      {status === "ready" ? (
        <>
          <RevealItem>
            <ReconciliationStrip rows={rows} report={report} />
          </RevealItem>

          <RevealItem>
            <CallTimeline
              calls={rows}
              selectedId={selectedId}
              onSelect={(call) => setSelectedId(call.call_id)}
            />
          </RevealItem>

          <RevealItem>
            <GuardrailPanel rows={rows} report={report} />
          </RevealItem>
        </>
      ) : (
        <RevealItem>
          <DataSurface
            status={status}
            skeletonRows={10}
            emptyTitle="No trace loaded"
            emptyHint="Agent calls appear here once a run has written them. No steps are reconstructed or approximated in the meantime."
            errorTitle="Trace unavailable"
            errorDetail="The trace query failed. No partial or reconstructed steps are shown."
            onRetry={() => {
              void run.refetch();
              void calls.refetch();
            }}
          />
        </RevealItem>
      )}

      <CallSheet call={selected} onClose={() => setSelectedId(null)} />
    </StagedReveal>
  );
}

function CrossCheck({
  label,
  summed,
  reported,
  matches,
}: {
  label: string;
  summed: string;
  reported: string;
  matches: boolean | null;
}) {
  return (
    <div
      className={cn(
        "rounded border bg-surface px-3 py-2",
        matches === false ? "border-destructive/60" : "border-border",
      )}
    >
      <div className="label-micro">{label}</div>
      <div className="tnum text-sm text-foreground">{summed}</div>
      <div className="tnum mt-0.5 text-xs text-muted-foreground">report: {reported}</div>
      <div
        className={cn(
          "label-micro mt-1",
          matches === null
            ? "text-muted-foreground"
            : matches
              ? "text-matched"
              : "text-destructive",
        )}
      >
        {matches === null ? "no report to check against" : matches ? "agrees" : "disagrees"}
      </div>
    </div>
  );
}

function ReconciliationStrip({
  rows,
  report,
}: {
  rows: AgentCallRow[];
  report: ReconciliationReport | null;
}) {
  const totals = totalAgentCalls(rows);

  return (
    <section className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
      <div className="rounded border border-border bg-surface px-3 py-2">
        <div className="label-micro">Calls traced</div>
        <div className="tnum text-sm text-foreground">{formatCount(totals.calls)}</div>
        <div className="tnum mt-0.5 text-xs text-muted-foreground">
          report llm_calls: {report ? formatCount(report.throughput.llm_calls) : "no report"}
        </div>
        <div
          className={cn(
            "label-micro mt-1",
            report
              ? totals.calls === report.throughput.llm_calls
                ? "text-matched"
                : "text-destructive"
              : "text-muted-foreground",
          )}
        >
          {report
            ? totals.calls === report.throughput.llm_calls
              ? "agrees"
              : "disagrees"
            : "no report to check against"}
        </div>
      </div>

      <CrossCheck
        label="Tokens in (summed)"
        summed={formatCount(totals.tokensIn)}
        reported={report ? formatCount(report.cost.tokens_in) : "no report"}
        matches={report ? totals.tokensIn === report.cost.tokens_in : null}
      />
      <CrossCheck
        label="Tokens out (summed)"
        summed={formatCount(totals.tokensOut)}
        reported={report ? formatCount(report.cost.tokens_out) : "no report"}
        matches={report ? totals.tokensOut === report.cost.tokens_out : null}
      />
      <CrossCheck
        label="Cost (summed)"
        summed={usd.format(totals.costUsd)}
        reported={report ? usd.format(report.cost.cost_usd) : "no report"}
        matches={report ? Math.abs(totals.costUsd - report.cost.cost_usd) < 1e-9 : null}
      />
    </section>
  );
}

function GuardrailPanel({
  rows,
  report,
}: {
  rows: AgentCallRow[];
  report: ReconciliationReport | null;
}) {
  const totals = totalAgentCalls(rows);
  const decided = totals.accepted + totals.rejected;
  const proposals = report ? report.guardrail.proposals : null;
  const rejectReasons = report ? report.guardrail.reject_reasons : {};

  return (
    <section className="panel p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-border pb-3">
        <div>
          <div className="label-micro">Guardrail decisions</div>
          <div className="tnum text-lg font-semibold text-foreground">
            {formatCount(totals.accepted)} accepted + {formatCount(totals.rejected)} rejected ={" "}
            {formatCount(decided)}
          </div>
        </div>
        <div className="text-right">
          <div className="label-micro">report.guardrail.proposals</div>
          <div className="tnum text-lg font-semibold text-foreground">
            {proposals === null ? "no report" : formatCount(proposals)}
          </div>
          <div
            className={cn(
              "label-micro",
              proposals === null
                ? "text-muted-foreground"
                : decided === proposals
                  ? "text-matched"
                  : "text-destructive",
            )}
          >
            {proposals === null
              ? "no report to check against"
              : decided === proposals
                ? "agrees"
                : `disagrees by ${formatCount(Math.abs(decided - proposals))}`}
          </div>
        </div>
      </div>

      <div className="grid gap-3 pt-3 md:grid-cols-2">
        <div>
          <div className="label-micro mb-1">Reject reasons — report</div>
          {Object.keys(rejectReasons).length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {report
                ? "report.guardrail.reject_reasons is empty."
                : "No report loaded for the selected run."}
            </p>
          ) : (
            <ul className="grid gap-1">
              {Object.entries(rejectReasons).map(([reason, count]) => (
                <li key={reason} className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-xs text-muted-foreground">{reason}</span>
                  <span className="tnum text-xs text-foreground">{formatCount(count)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <div className="label-micro mb-1">Reject reasons — summed from traced calls</div>
          {Object.keys(totals.reasonCounts).length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No guardrail reasons recorded on the traced calls.
            </p>
          ) : (
            <ul className="grid gap-1">
              {Object.entries(totals.reasonCounts).map(([reason, count]) => (
                <li key={reason} className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-xs text-muted-foreground">{reason}</span>
                  <span className="tnum text-xs text-foreground">{formatCount(count)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
