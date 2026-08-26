import { Check, ChevronsUpDown } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCurrentRun } from "@/lib/current-run";
import { formatCount } from "@/lib/format";
import { useRuns } from "@/lib/use-run-comparison";
import { useRunReport } from "@/lib/use-run-report";
import { cn } from "@/lib/utils";

/**
 * Run selector. Run identities, seeds and seed-sets come from the fetched
 * `runs` rows — nothing here is a placeholder. Selecting a run drives every
 * route through CurrentRunProvider; with no selection the panel follows the
 * newest run.
 */
export function RunSelector() {
  const runs = useRuns();
  const active = useRunReport();
  const { selectedRunId, selectRun } = useCurrentRun();

  const rows = runs.data ?? [];
  const activeRow = active.data;

  const summary = activeRow
    ? `${activeRow.run_id.slice(0, 8)} · seed ${
        activeRow.report ? formatCount(activeRow.report.config.seed) : "—"
      }${activeRow.report ? ` · ${activeRow.report.config.seed_set}` : ""}`
    : runs.isLoading || active.isLoading
      ? "loading runs…"
      : runs.isError || active.isError
        ? "runs unavailable"
        : "no runs available";

  const disabled = rows.length === 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        disabled={disabled}
        aria-label="Select reconciliation run"
        className="flex w-full min-w-0 items-center justify-between gap-3 rounded border border-border bg-surface px-3 py-1.5 text-left transition-colors hover:border-border-strong disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto sm:min-w-56"
      >
        <span className="flex min-w-0 flex-col leading-tight">
          <span className="label-micro">Run</span>
          <span className="tnum truncate text-sm text-foreground">{summary}</span>
        </span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="max-h-80 w-80 overflow-y-auto">
        <DropdownMenuLabel className="label-micro">
          {formatCount(rows.length)} run(s) · newest first
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuItem onSelect={() => selectRun(null)} className="gap-2">
          <Check
            className={cn("size-3.5", selectedRunId ? "opacity-0" : "opacity-100")}
            aria-hidden="true"
          />
          <span className="text-sm">Follow newest run</span>
        </DropdownMenuItem>

        {rows.map((row) => {
          const seed = row.report?.config.seed ?? row.config?.seed ?? null;
          const seedSet = row.report?.config.seed_set ?? row.config?.seed_set ?? null;
          return (
            <DropdownMenuItem
              key={row.run_id}
              onSelect={() => selectRun(row.run_id)}
              className="gap-2"
            >
              <Check
                className={cn(
                  "size-3.5",
                  selectedRunId === row.run_id ? "opacity-100" : "opacity-0",
                )}
                aria-hidden="true"
              />
              <span className="tnum flex min-w-0 flex-col leading-tight">
                <span className="truncate text-sm text-foreground">{row.run_id}</span>
                <span className="text-xs text-muted-foreground">
                  seed {seed === null ? "—" : formatCount(seed)} · {seedSet ?? "—"} · {row.status}
                </span>
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
