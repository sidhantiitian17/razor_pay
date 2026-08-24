import { createFileRoute } from "@tanstack/react-router";

import { DataSurface } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { useSurfaceStatus } from "@/hooks/use-surface-status";

export const Route = createFileRoute("/agent-trace")({
  head: () => ({
    meta: [
      { title: "Agent Trace — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Step-by-step trace of the reconciliation agent for a selected run, including seed and seed-set provenance.",
      },
      { property: "og:title", content: "Agent Trace — Settlement Reconciliation" },
      {
        property: "og:description",
        content: "Inspect each decision the recon agent made, in order, for one run.",
      },
    ],
  }),
  component: AgentTracePage,
});

function AgentTracePage() {
  const status = useSurfaceStatus();

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Agent Trace"
          description="Ordered decision trace for the selected run. Every step is attributed to the run's seed and seed-set so a trace can be reproduced exactly."
        />
      </RevealItem>

      <RevealItem>
        <DataSurface
          status={status}
          emptyTitle="No trace loaded"
          emptyHint="Select a run to stream its trace. Traces are only available once the data source is enabled."
          errorTitle="Trace unavailable"
          errorDetail="The trace query failed. No partial or reconstructed steps are shown."
          skeletonRows={10}
        />
      </RevealItem>
    </StagedReveal>
  );
}
