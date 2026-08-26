import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";

import { AblationPanel } from "@/components/dashboard/ablation-panel";
import { ComparisonTable } from "@/components/eval/comparison-table";
import { RequestRunForm } from "@/components/eval/request-run-form";
import { SeedDistribution } from "@/components/eval/seed-distribution";
import { DataSurface, type SurfaceStatus } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { ProductShell } from "@/components/shell/product-shell";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CheckRow } from "@/components/verify/check-row";
import { useAuth } from "@/hooks/use-auth";
import { computeControlRows } from "@/lib/anti-slop-checks";
import { formatCount } from "@/lib/format";
import { SEED_RANGE_SUMMARY } from "@/lib/seed-protocol";
import { splitSweep, useEvalSweeps } from "@/lib/use-eval-sweeps";
import { compareReports, useRuns, type RunListRow } from "@/lib/use-run-comparison";
import { useRunRequests } from "@/lib/use-run-requests";
import { cn } from "@/lib/utils";
import { useControlResults } from "@/lib/use-verify-inputs";

export const Route = createFileRoute("/_authenticated/eval-lab")({
  head: () => ({
    meta: [
      { title: "Eval Lab — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Holdout seed distribution with the worst seed as the gate value, ablation baselines, run-over-run metric deltas, negative controls, and run requests.",
      },
      { property: "og:title", content: "Eval Lab — Settlement Reconciliation" },
      {
        property: "og:description",
        content:
          "Twenty-seed holdout sweep, four ablation arms with lift and precision cost, and polarity-aware run comparison — dev seeds kept separate as tuning, not a claim.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: EvalLabRoute,
});

function EvalLabRoute() {
  return (
    <ProductShell>
      <EvalLabPage />
    </ProductShell>
  );
}

function runLabel(run: RunListRow): string {
  const seed = run.config ? `seed ${run.config.seed} (${run.config.seed_set})` : "seed unknown";
  return `${run.engine_version} · ${seed} · ${run.created_at}`;
}

function EvalLabPage() {
  const { session, loading: authLoading } = useAuth();
  const runs = useRuns();
  const rows = runs.data ?? [];

  const latest = rows[0]?.run_id;
  const previous = rows[1]?.run_id ?? rows[0]?.run_id;

  const [runIdA, setRunIdA] = useState<string | undefined>(undefined);
  const [runIdB, setRunIdB] = useState<string | undefined>(undefined);
  const selectedA = runIdA ?? previous;
  const selectedB = runIdB ?? latest;

  const runA = rows.find((run) => run.run_id === selectedA) ?? null;
  const runB = rows.find((run) => run.run_id === selectedB) ?? null;

  const sweeps = useEvalSweeps(selectedB);
  const controls = useControlResults(selectedB);
  const requests = useRunRequests(Boolean(session));

  const split = useMemo(() => splitSweep(sweeps.data ?? []), [sweeps.data]);
  const comparison = useMemo(
    () => compareReports(runA?.report ?? null, runB?.report ?? null),
    [runA?.report, runB?.report],
  );

  const reportB = runB?.report ?? null;
  const controlRows = reportB ? computeControlRows(reportB, controls.data ?? []) : [];

  const anyError = runs.isError || sweeps.isError || controls.isError;
  const anyPending =
    runs.isPending || (Boolean(selectedB) && (sweeps.isPending || controls.isPending));

  const status: SurfaceStatus = anyError
    ? "error"
    : anyPending || authLoading
      ? "loading"
      : reportB
        ? "ready"
        : "empty";

  const submitError = requests.insert.isError ? (requests.insert.error as Error).message : null;

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Eval Lab"
          description="Reported numbers come from the holdout sweep only; the worst holdout seed is the gate value. Dev seeds are tuning and are never a claim, and the regression seed is a snapshot, not a metric."
          actions={
            <div className="rounded border border-border bg-surface px-3 py-1.5">
              <div className="label-micro">Seed protocol</div>
              <div className="tnum text-xs text-foreground">{SEED_RANGE_SUMMARY}</div>
            </div>
          }
        />
      </RevealItem>

      {rows.length > 0 ? (
        <RevealItem>
          <section className="panel grid min-w-0 gap-3 p-4 sm:grid-cols-2">
            <div className="grid min-w-0 gap-1.5">
              <span className="label-micro">Run A — baseline</span>
              <Select value={selectedA ?? ""} onValueChange={setRunIdA}>
                <SelectTrigger className="min-w-0 [&>span]:truncate">
                  <SelectValue placeholder="select run" />
                </SelectTrigger>
                <SelectContent>
                  {rows.map((run) => (
                    <SelectItem key={run.run_id} value={run.run_id}>
                      {runLabel(run)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid min-w-0 gap-1.5">
              <span className="label-micro">Run B — candidate (drives every panel below)</span>
              <Select value={selectedB ?? ""} onValueChange={setRunIdB}>
                <SelectTrigger className="min-w-0 [&>span]:truncate">
                  <SelectValue placeholder="select run" />
                </SelectTrigger>
                <SelectContent>
                  {rows.map((run) => (
                    <SelectItem key={run.run_id} value={run.run_id}>
                      {runLabel(run)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </section>
        </RevealItem>
      ) : null}

      <RevealItem>
        <DataSurface
          status={status}
          skeletonRows={8}
          emptyTitle="No evaluations loaded"
          emptyHint="Every panel here reads the selected run's report and its eval_sweeps rows. Until the engine writes a run, nothing is displayed — no placeholder distribution, no placeholder deltas."
          errorTitle="Evaluation data unavailable"
          errorDetail="The evaluation queries failed, so rates, deltas and the gate value are withheld rather than shown stale."
          onRetry={() => {
            void runs.refetch();
            void sweeps.refetch();
            void controls.refetch();
          }}
        >
          {reportB ? (
            <div className="grid gap-4">
              <SeedDistribution split={split} />

              <AblationPanel ablation={reportB.ablation} />

              <ComparisonTable
                result={comparison}
                labelA={runA ? runLabel(runA) : "no run selected"}
                labelB={runB ? runLabel(runB) : "no run selected"}
              />

              <section className="panel">
                <header className="flex items-baseline justify-between gap-3 border-b border-border px-4 py-3">
                  <h2 className="text-sm font-semibold text-foreground">Negative controls</h2>
                  <span className="tnum text-xs text-muted-foreground">
                    {formatCount(controlRows.filter((row) => row.rowPassed !== null).length)} /{" "}
                    {formatCount(controlRows.length)} recorded ·{" "}
                    {formatCount(controlRows.filter((row) => row.disagrees).length)} disagree with
                    the report
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
            </div>
          ) : null}
        </DataSurface>
      </RevealItem>

      <RevealItem>
        <RequestRunForm
          signedIn={Boolean(session)}
          live={requests.live}
          pending={requests.insert.isPending}
          submitError={submitError}
          rows={requests.query.data ?? []}
          onSubmit={(config) => requests.insert.mutate(config)}
        />
      </RevealItem>
    </StagedReveal>
  );
}
