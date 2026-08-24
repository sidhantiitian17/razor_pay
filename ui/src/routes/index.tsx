import { createFileRoute } from "@tanstack/react-router";

import { DataSurface } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { useSurfaceStatus } from "@/hooks/use-surface-status";

export const Route = createFileRoute("/")({
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
    ],
  }),
  component: RunsPage,
});

/** Metric slots the Runs surface will render once the frozen contract lands. */
const HEADLINE_SLOTS = [
  { label: "Unresolved", note: "count of unresolved items, by bucket" },
  { label: "Match rate", note: "matched / in-scope, both shown" },
  { label: "Throughput", note: "with measurement mode" },
] as const;

function RunsPage() {
  const status = useSurfaceStatus();

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Runs"
          description="Every run carries its seed and seed-set, its unresolved buckets and its resolved tags as separate vocabularies, and amounts in integer paise rendered as INR only here."
        />
      </RevealItem>

      <RevealItem>
        <div className="grid gap-3 sm:grid-cols-3">
          {HEADLINE_SLOTS.map((slot) => (
            <div key={slot.label} className="panel p-4">
              <div className="label-micro">{slot.label}</div>
              <div className="tnum mt-1 text-2xl font-semibold text-muted-foreground">—</div>
              <p className="mt-1 text-xs text-muted-foreground">{slot.note}</p>
            </div>
          ))}
        </div>
      </RevealItem>

      <RevealItem>
        <DataSurface
          status={status}
          emptyTitle="No runs loaded"
          emptyHint="Runs appear once the reconciliation database is enabled and the frozen schema is applied. No figures are rendered before then."
          errorTitle="Run index unavailable"
          errorDetail="The data source did not respond. Nothing is displayed rather than a stale or synthetic figure."
        />
      </RevealItem>
    </StagedReveal>
  );
}
