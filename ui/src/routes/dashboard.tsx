import { createFileRoute } from "@tanstack/react-router";

import { AblationPanel } from "@/components/dashboard/ablation-panel";
import { ConfusionMatrix } from "@/components/dashboard/confusion-matrix";
import { CountUp, RateCard, StatCard } from "@/components/dashboard/stat-card";
import { VocabularyBars } from "@/components/dashboard/vocabulary-bars";
import { DataSurface, type SurfaceStatus } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { formatCount } from "@/lib/format";
import { useRunReport } from "@/lib/use-run-report";
import type { ReconciliationReport, UnresolvedMap } from "@/types/report";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Run Dashboard — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Match rate, resolved rate, unresolved count, throughput, cost and LLM p95 for a reconciliation run, each with its numerator and denominator.",
      },
      { property: "og:title", content: "Run Dashboard — Settlement Reconciliation" },
      {
        property: "og:description",
        content:
          "Institutional dashboard for one 3-way settlement reconciliation run: rates with provenance, confusion matrices, resolved tags and unresolved buckets, and baseline ablations.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: DashboardPage,
});

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});

function unresolvedTotal(unresolved: UnresolvedMap): number {
  return Object.values(unresolved).reduce((sum, value) => sum + value, 0);
}

function DashboardPage() {
  const query = useRunReport();
  const report = query.data?.report ?? null;

  const status: SurfaceStatus = query.isLoading
    ? "loading"
    : query.isError
      ? "error"
      : report
        ? "ready"
        : "empty";

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Run Dashboard"
          description="Every rate on this page prints its numerator and denominator. Resolved tags and unresolved buckets are separate vocabularies and are never summed."
          actions={report ? <SeedBadge report={report} /> : undefined}
        />
      </RevealItem>

      <RevealItem>
        <DataSurface
          status={status}
          skeletonRows={8}
          emptyTitle="No run report yet"
          emptyHint="This dashboard reads the selected run's report column. Until the reconciliation engine writes a report, nothing is displayed — no placeholder figures are shown."
          errorTitle="Run report unavailable"
          errorDetail="The report could not be read from the data source, so no figure is rendered rather than a stale or synthetic one."
          onRetry={() => void query.refetch()}
        >
          {report ? <DashboardBody report={report} /> : null}
        </DataSurface>
      </RevealItem>
    </StagedReveal>
  );
}

function SeedBadge({ report }: { report: ReconciliationReport }) {
  return (
    <div className="flex items-center gap-2">
      <div className="rounded border border-border bg-surface px-3 py-1.5">
        <div className="label-micro">Seed</div>
        <div className="tnum text-sm text-foreground">{formatCount(report.config.seed)}</div>
      </div>
      <div className="rounded border border-border bg-surface px-3 py-1.5">
        <div className="label-micro">Seed set</div>
        <div className="tnum text-sm text-foreground">{report.config.seed_set}</div>
      </div>
      <div className="rounded border border-border bg-surface px-3 py-1.5">
        <div className="label-micro">Engine</div>
        <div className="tnum text-sm text-foreground">{report.engine_version}</div>
      </div>
    </div>
  );
}

function DashboardBody({ report }: { report: ReconciliationReport }) {
  const { accuracy, throughput, cost, candidate_space, ablation, resolved, unresolved } = report;
  const unresolvedCount = unresolvedTotal(unresolved);
  const replay = throughput.measurement_mode === "replay";

  return (
    <div className="grid gap-4">
      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <StatCard
          label="Unresolved"
          tone="unresolved"
          value={<CountUp value={unresolvedCount} format={(n) => formatCount(Math.round(n))} />}
          denominatorLine={`${formatCount(accuracy.unresolved_rate.numerator)} / ${formatCount(accuracy.unresolved_rate.denominator)} in-scope items · ${(accuracy.unresolved_rate.value * 100).toFixed(2)}%`}
          note="Sum of the unresolved buckets — the honest number. Never combined with resolved tags."
        />

        <RateCard
          label="Match rate"
          tone="signal"
          metric={accuracy.match_rate}
          unitLabel="in-scope items"
        />

        <RateCard
          label="Resolved rate"
          metric={accuracy.resolved_rate}
          unitLabel="matched groups"
        />

        <StatCard
          label="Throughput"
          value={
            <CountUp
              value={throughput.rows_per_second_end_to_end.value}
              format={(n) => `${n.toFixed(1)} rows/s`}
            />
          }
          denominatorLine={`${formatCount(throughput.rows_per_second_end_to_end.numerator)} rows / ${formatCount(throughput.rows_per_second_end_to_end.denominator)} s end-to-end`}
          badge={
            <span className="label-micro rounded border border-border px-1.5 py-0.5 text-foreground/80">
              {throughput.measurement_mode}
            </span>
          }
          note={
            replay
              ? `Measurement mode: replay over ${formatCount(throughput.runs_measured)} run(s) — not a performance claim.`
              : `Measurement mode: live over ${formatCount(throughput.runs_measured)} run(s), median wall clock ${throughput.wall_clock_seconds_median.toFixed(2)} s.`
          }
        />

        <StatCard
          label="Cost"
          value={<CountUp value={cost.cost_usd} format={(n) => usd.format(n)} />}
          denominatorLine={`${usd.format(cost.cost_per_100_rows_usd)} per 100 rows · ${formatCount(cost.tokens_in)} in / ${formatCount(cost.tokens_out)} out tokens`}
          note={`Cache hit rate ${(cost.cache_hit_rate * 100).toFixed(2)}% · pricing last verified ${cost.pricing_last_verified}`}
        />

        <StatCard
          label="LLM p95"
          value={<CountUp value={throughput.llm_p95_ms} format={(n) => `${n.toFixed(0)} ms`} />}
          denominatorLine={`p50 ${formatCount(throughput.llm_p50_ms)} ms · ${formatCount(throughput.llm_calls)} calls · ${formatCount(throughput.llm_retries)} retries`}
          note={`Agent turns mean ${throughput.agent_turns.mean.toFixed(2)}, max ${formatCount(throughput.agent_turns.max)}, single-turn ${(throughput.agent_turns.single_turn_fraction * 100).toFixed(2)}%`}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <ConfusionMatrix
          title="Bank ↔ payout links"
          metrics={accuracy.links.bank_payout}
          candidateSpaceSize={candidate_space.size}
        />
        <ConfusionMatrix
          title="Payout ↔ ledger links"
          metrics={accuracy.links.payout_ledger}
          candidateSpaceSize={candidate_space.size}
        />
      </section>

      <section className="panel flex flex-wrap items-baseline justify-between gap-3 p-4">
        <div>
          <div className="label-micro">Candidate space</div>
          <div className="tnum text-lg font-semibold text-foreground">
            {formatCount(candidate_space.size)} pairs
          </div>
        </div>
        <div className="text-right">
          <div className="label-micro">Blocker recall</div>
          <div className="tnum text-lg font-semibold text-foreground">
            {(candidate_space.blocker_recall.value * 100).toFixed(2)}%
            <span className="ml-2 text-xs text-muted-foreground">
              {formatCount(candidate_space.blocker_recall.numerator)} /{" "}
              {formatCount(candidate_space.blocker_recall.denominator)} true pairs retained
            </span>
          </div>
        </div>
      </section>

      <VocabularyBars resolved={resolved} unresolved={unresolved} />

      <AblationPanel ablation={ablation} />
    </div>
  );
}
