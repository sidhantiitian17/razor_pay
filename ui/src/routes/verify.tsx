import { createFileRoute } from "@tanstack/react-router";

import { DataSurface } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { useSurfaceStatus } from "@/hooks/use-surface-status";

export const Route = createFileRoute("/verify")({
  head: () => ({
    meta: [
      { title: "Verify — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Reproduce a reconciliation run from its seed and seed-set and verify reported figures against the source report.",
      },
      { property: "og:title", content: "Verify — Settlement Reconciliation" },
      {
        property: "og:description",
        content: "Seed-level reproduction and figure verification for recon runs.",
      },
    ],
  }),
  component: VerifyPage,
});

function VerifyPage() {
  const status = useSurfaceStatus();

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Verify"
          description="Reproduce a run from its seed and seed-set, then diff every displayed figure against the source report. Nothing on this screen is authored by hand."
        />
      </RevealItem>

      <RevealItem>
        <DataSurface
          status={status}
          emptyTitle="Nothing to verify yet"
          emptyHint="Verification needs a run report from the data source, plus the generated report types."
          errorTitle="Verification unavailable"
          errorDetail="The report could not be fetched, so no figure can be verified."
        />
      </RevealItem>
    </StagedReveal>
  );
}
