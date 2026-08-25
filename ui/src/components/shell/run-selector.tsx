import { ChevronsUpDown } from "lucide-react";

import { useConnectionState } from "./connection-status";

/**
 * Run selector. Run identities, seeds and seed-sets come from fetched data;
 * with no data source configured there is nothing to select and the control
 * says so instead of showing a placeholder run.
 */
export function RunSelector() {
  const state = useConnectionState();
  const disabled = state !== "online";

  return (
    <button
      type="button"
      disabled={disabled}
      aria-label="Select reconciliation run"
      className="flex w-full min-w-0 items-center justify-between gap-3 rounded border border-border bg-surface px-3 py-1.5 text-left transition-colors hover:border-border-strong disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto sm:min-w-56"
    >
      <span className="flex flex-col leading-tight">
        <span className="label-micro">Run</span>
        <span className="tnum text-sm text-foreground">
          {disabled ? "no runs available" : "select run"}
        </span>
      </span>
      <ChevronsUpDown className="size-3.5 text-muted-foreground" aria-hidden="true" />
    </button>
  );
}
