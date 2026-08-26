import { createFileRoute, useSearch } from "@tanstack/react-router";

import { DataSurface } from "@/components/shell/data-surface";
import type { SurfaceStatus } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { ProductShell } from "@/components/shell/product-shell";
import { useCurrentRun } from "@/lib/current-run";
import { formatCount } from "@/lib/format";
import { useRuns, type RunListRow } from "@/lib/use-run-comparison";
import { useRunReport } from "@/lib/use-run-report";
import { cn } from "@/lib/utils";
import type { ReconciliationReport, UnresolvedMap } from "@/types/report";

export const Route = createFileRoute("/_authenticated/runs")({
  validateSearch: (search: Record<string, unknown>): { state?: SurfaceStatus } => {
    const state = search["state"];
    if (state === "loading" || state === "empty" || state === "error") return { state };
    return {};
  },
  head: () => ({
    meta: [
      { title: "Runs — 3-Way Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Reconciliation runs across bank, gateway payout and ledger, with match rate, unresolved buckets, seed and seed-set for every run.",
      },
      { property: "og:title", content: "Runs — 3-Way Settlement Reconciliation" },
      {
        property: "og:description",
        content:
          "Institutional control panel for bank / gateway payout / ledger settlement reconciliation runs.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: RunsRoute,
});

function RunsRoute() {
  return (
    <ProductShell>
      <RunsPage />
    </ProductShell>
  );
}

function unresolvedTotal(unresolved: UnresolvedMap): number {
  return Object.values(unresolved).reduce((sum, value) => sum + value, 0);
}

function RunsPage() {
  const override = useSearch({ strict: false, select: (search) => search.state });
  const runs = useRuns();
  const active = useRunReport();

  const rows = runs.data ?? [];
  const activeReport = active.data?.report ?? null;

  const status: SurfaceStatus =
    override === "loading" || override === "empty" || override === "error"
      ? override
      : runs.isLoading || active.isLoading
        ? "loading"
        : runs.isError || active.isError
          ? "error"
          : rows.length === 0
            ? "empty"
            : "ready";

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Runs"
          description="Every run carries its seed and seed-set, its unresolved buckets and its resolved tags as separate vocabularies, and amounts in integer paise rendered as INR only here."
          actions={
            active.data ? (
              <div className="tnum text-right text-xs text-muted-foreground">
                <div>
                  Selected run <span className="text-foreground">{active.data.run_id}</span>
                </div>
                {activeReport ? (
                  <div>
                    seed {formatCount(activeReport.config.seed)} · seed-set{" "}
                    {activeReport.config.seed_set} · engine {active.data.engine_version}
                  </div>
                ) : null}
              </div>
            ) : undefined
          }
        />
      </RevealItem>

      {status === "ready" && activeReport ? (
        <RevealItem>
          <HeadlineTiles report={activeReport} />
        </RevealItem>
      ) : null}

      <RevealItem>
        <DataSurface
          status={status}
          skeletonRows={6}
          emptyTitle="No runs loaded"
          emptyHint="No rows exist in the runs table yet. No figures are rendered before then."
          errorTitle="Run index unavailable"
          errorDetail="The data source did not respond. Nothing is displayed rather than a stale or synthetic figure."
          onRetry={() => {
            void runs.refetch();
            void active.refetch();
          }}
        >
          <RunTable rows={rows} />
        </DataSurface>
      </RevealItem>
    </StagedReveal>
  );
}

function Tile({
  label,
  value,
  denominator,
  note,
  prominent,
}: {
  label: string;
  value: string;
  denominator: string;
  note: string;
  prominent?: boolean;
}) {
  return (
    <div className={cn("panel p-4", prominent && "border-unresolved/60")}>
      <div className="label-micro">{label}</div>
      <div
        className={cn(
          "tnum mt-1 text-2xl font-semibold",
          prominent ? "text-unresolved" : "text-foreground",
        )}
      >
        {value}
      </div>
      <div className="tnum mt-1 text-xs text-muted-foreground">{denominator}</div>
      <p className="mt-1 text-xs text-muted-foreground">{note}</p>
    </div>
  );
}

function HeadlineTiles({ report }: { report: ReconciliationReport }) {
  const { accuracy, throughput, unresolved } = report;
  const replay = throughput.measurement_mode === "replay";

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Tile
        prominent
        label="Unresolved"
        value={formatCount(unresolvedTotal(unresolved))}
        denominator={`${formatCount(accuracy.unresolved_rate.numerator)} / ${formatCount(accuracy.unresolved_rate.denominator)} in-scope items · ${(accuracy.unresolved_rate.value * 100).toFixed(2)}%`}
        note="Sum of the unresolved buckets, never combined with resolved tags."
      />
      <Tile
        label="Match rate"
        value={`${(accuracy.match_rate.value * 100).toFixed(2)}%`}
        denominator={`${formatCount(accuracy.match_rate.numerator)} / ${formatCount(accuracy.match_rate.denominator)} in-scope items`}
        note="Matched and in-scope both shown."
      />
      <Tile
        label="Throughput"
        value={`${throughput.rows_per_second_end_to_end.value.toFixed(1)} rows/s`}
        denominator={`${formatCount(throughput.rows_per_second_end_to_end.numerator)} rows / ${formatCount(throughput.rows_per_second_end_to_end.denominator)} s end-to-end`}
        note={
          replay
            ? `Measurement mode: replay over ${formatCount(throughput.runs_measured)} run(s) — not a performance claim.`
            : `Measurement mode: live over ${formatCount(throughput.runs_measured)} run(s).`
        }
      />
    </div>
  );
}

function RunTable({ rows }: { rows: RunListRow[] }) {
  const { selectedRunId, selectRun } = useCurrentRun();

  return (
    <div className="panel w-full max-w-full overflow-x-auto">
      <table className="w-full min-w-[52rem] border-collapse text-sm">
        <caption className="sr-only">
          Reconciliation runs with seed, seed-set, match rate and unresolved count
        </caption>
        <thead>
          <tr className="border-b border-border text-left">
            <th scope="col" className="label-micro px-3 py-2">
              Run
            </th>
            <th scope="col" className="label-micro px-3 py-2">
              Seed
            </th>
            <th scope="col" className="label-micro px-3 py-2">
              Seed set
            </th>
            <th scope="col" className="label-micro px-3 py-2">
              Mode
            </th>
            <th scope="col" className="label-micro px-3 py-2">
              Status
            </th>
            <th scope="col" className="label-micro px-3 py-2">
              Match rate
            </th>
            <th scope="col" className="label-micro px-3 py-2">
              Unresolved
            </th>
            <th scope="col" className="label-micro px-3 py-2">
              Created
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const report = row.report;
            const config = report?.config ?? row.config ?? null;
            const isSelected = selectedRunId === row.run_id;
            return (
              <tr
                key={row.run_id}
                onClick={() => selectRun(row.run_id)}
                aria-selected={isSelected}
                className={cn(
                  "tnum cursor-pointer border-b border-border/60 transition-colors hover:bg-muted/40",
                  isSelected && "bg-muted/60",
                )}
              >
                <td className="px-3 py-2 text-foreground">{row.run_id}</td>
                <td className="px-3 py-2">{config ? formatCount(config.seed) : "—"}</td>
                <td className="px-3 py-2">{config?.seed_set ?? "—"}</td>
                <td className="px-3 py-2">{config?.mode ?? "—"}</td>
                <td className="px-3 py-2">{row.status}</td>
                <td className="px-3 py-2">
                  {report
                    ? `${(report.accuracy.match_rate.value * 100).toFixed(2)}% (${formatCount(report.accuracy.match_rate.numerator)}/${formatCount(report.accuracy.match_rate.denominator)})`
                    : "—"}
                </td>
                <td className="px-3 py-2 text-unresolved">
                  {report ? formatCount(unresolvedTotal(report.unresolved)) : "—"}
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {new Date(row.created_at).toISOString().replace("T", " ").slice(0, 19)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
