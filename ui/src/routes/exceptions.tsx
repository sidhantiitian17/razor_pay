import { createFileRoute } from "@tanstack/react-router";

import { DataSurface } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { useSurfaceStatus } from "@/hooks/use-surface-status";

export const Route = createFileRoute("/exceptions")({
  head: () => ({
    meta: [
      { title: "Exceptions — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Unresolved buckets and resolved tags kept as separate vocabularies, never summed into one total.",
      },
      { property: "og:title", content: "Exceptions — Settlement Reconciliation" },
      {
        property: "og:description",
        content: "Triage unresolved settlement exceptions bucket by bucket.",
      },
    ],
  }),
  component: ExceptionsPage,
});

function ExceptionsPage() {
  const status = useSurfaceStatus();

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Exceptions"
          description="Unresolved buckets and resolved tags are distinct vocabularies and are reported side by side, never added together."
        />
      </RevealItem>

      <RevealItem>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="panel p-4">
            <div className="label-micro">Unresolved buckets</div>
            <p className="mt-1 text-xs text-muted-foreground">
              Bucket names and counts come from the run report.
            </p>
          </div>
          <div className="panel p-4">
            <div className="label-micro">Resolved tags</div>
            <p className="mt-1 text-xs text-muted-foreground">
              Tag taxonomy is independent of the bucket taxonomy.
            </p>
          </div>
        </div>
      </RevealItem>

      <RevealItem>
        <DataSurface
          status={status}
          emptyTitle="No exceptions loaded"
          emptyHint="Bucketed exceptions load with a selected run once the data source is enabled."
          errorTitle="Exception feed unavailable"
          errorDetail="The exception query failed. Counts are withheld rather than approximated."
        />
      </RevealItem>
    </StagedReveal>
  );
}
