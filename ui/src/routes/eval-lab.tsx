import { createFileRoute } from "@tanstack/react-router";

import { DataSurface } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { useSurfaceStatus } from "@/hooks/use-surface-status";

export const Route = createFileRoute("/eval-lab")({
  head: () => ({
    meta: [
      { title: "Eval Lab — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Compare reconciliation runs across seed-sets, with throughput reported alongside its measurement mode.",
      },
      { property: "og:title", content: "Eval Lab — Settlement Reconciliation" },
      {
        property: "og:description",
        content: "Seed-set comparisons and measured throughput for the recon engine.",
      },
    ],
  }),
  component: EvalLabPage,
});

function EvalLabPage() {
  const status = useSurfaceStatus();

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Eval Lab"
          description="Run-over-run comparison across seed-sets. Throughput is always shown with its measurement mode; replay figures are labelled as not a performance claim."
        />
      </RevealItem>

      <RevealItem>
        <div className="panel p-4">
          <div className="label-micro">Throughput measurement mode</div>
          <p className="mt-1 text-xs text-muted-foreground">
            Mode is read from the report — live measurement or replay. A replay figure is rendered
            with the notice “not a performance claim”.
          </p>
        </div>
      </RevealItem>

      <RevealItem>
        <DataSurface
          status={status}
          emptyTitle="No evaluations loaded"
          emptyHint="Comparisons need at least one completed run from the data source."
          errorTitle="Evaluation data unavailable"
          errorDetail="The evaluation query failed. Rates and throughput are withheld."
        />
      </RevealItem>
    </StagedReveal>
  );
}
