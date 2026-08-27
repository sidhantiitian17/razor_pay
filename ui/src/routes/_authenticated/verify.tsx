import { createFileRoute } from "@tanstack/react-router";

import { CheckRow, VerdictBadge } from "@/components/verify/check-row";
import { DataSurface, type SurfaceStatus } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { ProductShell } from "@/components/shell/product-shell";
import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  computeAntiSlopChecks,
  computeControlRows,
  computeFalsifiers,
  type VerifyInputs,
} from "@/lib/anti-slop-checks";
import { useAgentCalls } from "@/lib/use-agent-calls";
import { useExceptions } from "@/lib/use-exceptions";
import { useRunReport } from "@/lib/use-run-report";
import { useClosures, useControlResults } from "@/lib/use-verify-inputs";

export const Route = createFileRoute("/_authenticated/verify")({
  head: () => ({
    meta: [
      { title: "Verify — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Eight anti-slop checks, six negative controls and the falsification statement, each computed at render time from the fetched run data with its evidence shown.",
      },
      { property: "og:title", content: "Verify — Settlement Reconciliation" },
      {
        property: "og:description",
        content:
          "Every verdict on this page is derived from fetched rows — checks, controls and falsifiers all print the evidence that produced them.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: VerifyRoute,
});

function VerifyRoute() {
  return (
    <ProductShell>
      <VerifyPage />
    </ProductShell>
  );
}

function VerifyPage() {
  const run = useRunReport();
  const runId = run.data?.run_id;
  const calls = useAgentCalls(runId);
  const controls = useControlResults(runId);
  const closures = useClosures(runId);
  const exceptions = useExceptions(runId);

  const report = run.data?.report ?? null;

  // Closures is intentionally service_role-only for regular operators; a
  // permission-denied response is swallowed as an empty array by useClosures
  // (see fetchClosures), so closures.isError never fires for that case.
  // Exclude closures from the page-wide error gate regardless: a closures
  // query failure must not blank the rest of the Verify page.
  const anyError = run.isError || calls.isError || controls.isError || exceptions.isError;
  const anyPending =
    run.isPending ||
    (Boolean(runId) &&
      (calls.isPending || controls.isPending || closures.isPending || exceptions.isPending));

  const status: SurfaceStatus = anyError
    ? "error"
    : anyPending
      ? "loading"
      : report
        ? "ready"
        : "empty";

  const inputs: VerifyInputs | null = report
    ? {
        report,
        calls: calls.data ?? [],
        closures: closures.data ?? [],
        exceptions: exceptions.data ?? [],
      }
    : null;

  const checks = inputs ? computeAntiSlopChecks(inputs) : [];
  const controlRows = inputs ? computeControlRows(inputs.report, controls.data ?? []) : [];
  const falsifiers = inputs ? computeFalsifiers(inputs, controlRows) : [];

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Verify"
          description="Every verdict below is computed at render time from the fetched rows and prints the evidence that produced it. No check is written as a constant in the page."
          actions={
            report ? (
              <div className="flex flex-wrap items-center justify-start gap-2 sm:justify-end">
                <div className="rounded border border-border bg-surface px-3 py-1.5">
                  <div className="label-micro">Seed</div>
                  <div className="tnum text-sm text-foreground">
                    {formatCount(report.config.seed)}
                  </div>
                </div>
                <div className="rounded border border-border bg-surface px-3 py-1.5">
                  <div className="label-micro">Seed set</div>
                  <div className="tnum text-sm text-foreground">{report.config.seed_set}</div>
                </div>
              </div>
            ) : undefined
          }
        />
      </RevealItem>

      {status === "ready" && inputs ? (
        <>
          <RevealItem>
            <section className="panel">
              <header className="flex items-baseline justify-between gap-3 border-b border-border px-4 py-3">
                <h2 className="text-sm font-semibold text-foreground">Anti-slop checks</h2>
                <span className="tnum text-xs text-muted-foreground">
                  {formatCount(checks.filter((check) => check.verdict === "pass").length)} pass ·{" "}
                  {formatCount(checks.filter((check) => check.verdict === "fail").length)} fail ·{" "}
                  {formatCount(checks.filter((check) => check.verdict === "vacuous").length)}{" "}
                  vacuous / {formatCount(checks.length)} checks
                </span>
              </header>
              <ol>
                {checks.map((check, index) => (
                  <CheckRow
                    key={check.id}
                    index={index + 1}
                    name={check.name}
                    verdict={check.verdict}
                    evidence={check.evidence}
                  />
                ))}
              </ol>
            </section>
          </RevealItem>

          <RevealItem>
            <section className="panel">
              <header className="flex items-baseline justify-between gap-3 border-b border-border px-4 py-3">
                <h2 className="text-sm font-semibold text-foreground">Negative controls</h2>
                <span className="tnum text-xs text-muted-foreground">
                  {formatCount(controlRows.filter((row) => row.rowPassed !== null).length)} /{" "}
                  {formatCount(controlRows.length)} recorded ·{" "}
                  {formatCount(controlRows.filter((row) => row.disagrees).length)} disagree with the
                  report
                </span>
              </header>
              <ol>
                {controlRows.map((row, index) => (
                  <CheckRow
                    key={row.name}
                    index={index + 1}
                    name={row.name}
                    verdict={row.verdict}
                    evidence={row.evidence}
                    aside={
                      <p
                        className={cn(
                          "tnum mt-1 font-mono text-xs",
                          row.disagrees ? "text-destructive" : "text-muted-foreground",
                        )}
                      >
                        control_results.passed ={" "}
                        {row.rowPassed === null ? "not yet run" : String(row.rowPassed)} ·
                        report.controls.{row.name}.passed ={" "}
                        {row.reportPassed === null ? "absent" : String(row.reportPassed)}
                        {row.disagrees ? " — sources disagree" : ""}
                      </p>
                    }
                  />
                ))}
              </ol>
            </section>
          </RevealItem>

          <RevealItem>
            <section className="panel">
              <header className="border-b border-border px-4 py-3">
                <h2 className="text-sm font-semibold text-foreground">Falsification statement</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  This work is wrong if any of the following holds. Each claim is published up
                  front; the verdict beside it is computed live for the selected run.
                </p>
              </header>
              <ol>
                {falsifiers.map((falsifier, index) => (
                  <li
                    key={falsifier.claim}
                    className="flex gap-3 border-b border-border/60 px-4 py-3 last:border-b-0"
                  >
                    <span className="tnum w-5 shrink-0 text-xs text-muted-foreground">
                      {index + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-3">
                        <span className="text-sm text-foreground">{falsifier.claim}</span>
                        <span
                          className={cn(
                            "label-micro shrink-0 rounded border px-1.5 py-0.5",
                            falsifier.verdict === "triggered"
                              ? "border-destructive/60 text-destructive"
                              : falsifier.verdict === "holds"
                                ? "border-matched/50 text-matched"
                                : "border-border-strong text-muted-foreground",
                          )}
                        >
                          {falsifier.verdict === "holds"
                            ? "not triggered"
                            : falsifier.verdict === "triggered"
                              ? "triggered"
                              : "not yet computable"}
                        </span>
                      </div>
                      <p className="tnum mt-1 break-words font-mono text-xs leading-relaxed text-muted-foreground">
                        {falsifier.evidence}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          </RevealItem>

          <RevealItem>
            <section className="panel flex flex-wrap items-center gap-3 p-4 text-xs text-muted-foreground">
              <VerdictBadge verdict="vacuous" />
              <span>
                A vacuous verdict means the check had nothing to examine for this run — it is not a
                pass. Counts of what was searched are printed with every check.
              </span>
            </section>
          </RevealItem>
        </>
      ) : (
        <RevealItem>
          <DataSurface
            status={status}
            emptyTitle="Nothing to verify yet"
            emptyHint="These checks read the selected run's report, agent calls, controls, closures and exceptions. Until a run exists there is nothing to compute, and no verdict is shown."
            errorTitle="Verification unavailable"
            errorDetail="One of the verification queries failed, so no verdict is rendered rather than one derived from partial data."
            onRetry={() => {
              void run.refetch();
              void calls.refetch();
              void controls.refetch();
              void closures.refetch();
              void exceptions.refetch();
            }}
          />
        </RevealItem>
      )}
    </StagedReveal>
  );
}
