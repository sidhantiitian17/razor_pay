import { createFileRoute } from "@tanstack/react-router";
import { Download } from "lucide-react";
import { useMemo, useState } from "react";

import { DataSurface } from "@/components/shell/data-surface";
import { PageHeader, RevealItem, StagedReveal } from "@/components/shell/page-states";
import { ProductShell } from "@/components/shell/product-shell";
import { ExceptionSheet } from "@/components/exceptions/exception-sheet";
import { ExceptionTable } from "@/components/exceptions/exception-table";
import { FilterBar, type FacetOption } from "@/components/exceptions/filter-bar";
import { useAuth } from "@/hooks/use-auth";
import { downloadCsv, exceptionsToCsv } from "@/lib/csv";
import { formatCount } from "@/lib/format";
import { useRunReport } from "@/lib/use-run-report";
import { UNRESOLVED_STATUSES, useExceptions, type ExceptionRow } from "@/lib/use-exceptions";
import { useTriage, type TriageAction } from "@/lib/use-triage";

export const Route = createFileRoute("/_authenticated/exceptions")({
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
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: ExceptionsRoute,
});

function ExceptionsRoute() {
  return (
    <ProductShell>
      <ExceptionsPage />
    </ProductShell>
  );
}

function facets(rows: ExceptionRow[], key: keyof ExceptionRow): FacetOption[] {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const value = String(row[key]);
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((entry) => entry !== value) : [...list, value];
}

function ExceptionsPage() {
  const run = useRunReport();
  const runId = run.data?.run_id;
  const exceptions = useExceptions(runId);
  const { assigneeLabel } = useAuth();
  const triage = useTriage(runId);

  const [selectedBuckets, setSelectedBuckets] = useState<string[]>([]);
  const [selectedSeverities, setSelectedSeverities] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const rows = exceptions.data ?? [];

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return rows.filter((row) => {
      if (selectedBuckets.length && !selectedBuckets.includes(row.bucket)) return false;
      if (selectedSeverities.length && !selectedSeverities.includes(row.severity)) return false;
      if (selectedStatuses.length && !selectedStatuses.includes(row.status)) return false;
      if (!needle) return true;
      if (row.exception_id.toLowerCase().includes(needle)) return true;
      return row.row_ids.some((id) => id.toLowerCase().includes(needle));
    });
  }, [rows, selectedBuckets, selectedSeverities, selectedStatuses, search]);

  const unresolvedInView = filtered.filter((row) => UNRESOLVED_STATUSES.includes(row.status));
  const selected = filtered.find((row) => row.exception_id === selectedId) ?? null;

  const status =
    run.isError || exceptions.isError
      ? "error"
      : run.isPending || (Boolean(runId) && exceptions.isPending)
        ? "loading"
        : rows.length === 0
          ? "empty"
          : "ready";

  function onAction(action: TriageAction) {
    if (!selected) return;
    triage.mutate({ exceptionId: selected.exception_id, action });
  }

  function onExport() {
    if (!runId) return;
    const day = new Date().toISOString().slice(0, 10);
    downloadCsv(`exceptions-unresolved-${runId}-${day}.csv`, exceptionsToCsv(unresolvedInView));
  }

  return (
    <StagedReveal>
      <RevealItem>
        <PageHeader
          title="Exception workqueue"
          description="Unresolved buckets and resolved tags are distinct vocabularies and are reported side by side, never added together."
          actions={
            status === "ready" ? (
              <button
                type="button"
                onClick={onExport}
                className="inline-flex items-center gap-2 rounded border border-border bg-surface px-3 py-1.5 text-xs text-foreground transition-colors hover:border-border-strong"
              >
                <Download className="size-3.5" aria-hidden="true" />
                Export unresolved as CSV ({formatCount(unresolvedInView.length)})
              </button>
            ) : undefined
          }
        />
      </RevealItem>

      {status === "ready" ? (
        <>
          <RevealItem>
            <FilterBar
              buckets={facets(rows, "bucket")}
              severities={facets(rows, "severity")}
              statuses={facets(rows, "status")}
              selectedBuckets={selectedBuckets}
              selectedSeverities={selectedSeverities}
              selectedStatuses={selectedStatuses}
              onToggleBucket={(value) => setSelectedBuckets((list) => toggle(list, value))}
              onToggleSeverity={(value) => setSelectedSeverities((list) => toggle(list, value))}
              onToggleStatus={(value) => setSelectedStatuses((list) => toggle(list, value))}
              search={search}
              onSearch={setSearch}
            />
          </RevealItem>

          <RevealItem>
            <div className="flex flex-wrap items-baseline gap-4 px-1 text-xs text-muted-foreground">
              <span className="tnum">
                showing {formatCount(filtered.length)} of {formatCount(rows.length)} exceptions
              </span>
              <span className="tnum">
                unresolved in view {formatCount(unresolvedInView.length)} /{" "}
                {formatCount(filtered.length)}
              </span>
            </div>
          </RevealItem>

          <RevealItem>
            <ExceptionTable
              rows={filtered}
              selectedId={selectedId}
              onSelect={(row) => setSelectedId(row.exception_id)}
            />
          </RevealItem>
        </>
      ) : (
        <RevealItem>
          <DataSurface
            status={status}
            emptyTitle="No exceptions loaded"
            emptyHint="Bucketed exceptions appear here once a run has been written to the database."
            errorTitle="Exception feed unavailable"
            errorDetail="The exception query failed. Counts are withheld rather than approximated."
            onRetry={() => {
              void run.refetch();
              void exceptions.refetch();
            }}
          />
        </RevealItem>
      )}

      <ExceptionSheet
        exception={selected}
        runId={runId}
        assigneeLabel={assigneeLabel}
        pending={triage.isPending}
        onAction={onAction}
        onClose={() => setSelectedId(null)}
      />
    </StagedReveal>
  );
}
