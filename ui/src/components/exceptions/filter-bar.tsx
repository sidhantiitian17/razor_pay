import { Search } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatCount } from "@/lib/format";

export interface FacetOption {
  value: string;
  count: number;
}

function FacetGroup({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: FacetOption[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  if (options.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="label-micro mr-1">{label}</span>
      {options.map((option) => {
        const active = selected.includes(option.value);
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onToggle(option.value)}
            className={cn(
              "flex items-center gap-1.5 rounded border px-2 py-1 text-xs transition-colors",
              active
                ? "border-primary/60 bg-primary/10 text-foreground"
                : "border-border bg-surface text-muted-foreground hover:border-border-strong",
            )}
          >
            <span className="font-medium">{option.value}</span>
            <span className="tnum text-[11px] text-muted-foreground">
              {formatCount(option.count)}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function FilterBar({
  buckets,
  severities,
  statuses,
  selectedBuckets,
  selectedSeverities,
  selectedStatuses,
  onToggleBucket,
  onToggleSeverity,
  onToggleStatus,
  search,
  onSearch,
}: {
  buckets: FacetOption[];
  severities: FacetOption[];
  statuses: FacetOption[];
  selectedBuckets: string[];
  selectedSeverities: string[];
  selectedStatuses: string[];
  onToggleBucket: (value: string) => void;
  onToggleSeverity: (value: string) => void;
  onToggleStatus: (value: string) => void;
  search: string;
  onSearch: (value: string) => void;
}) {
  return (
    <div className="panel grid gap-3 p-3">
      <label className="flex items-center gap-2 rounded border border-border bg-background px-2.5 py-1.5">
        <Search className="size-3.5 text-muted-foreground" aria-hidden="true" />
        <span className="sr-only">Search exception or source row ID</span>
        <input
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder="Search exception ID or source row ID (BNK- / pout_SYNTH / LED-)"
          className="tnum w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        />
      </label>

      <FacetGroup
        label="Bucket"
        options={buckets}
        selected={selectedBuckets}
        onToggle={onToggleBucket}
      />
      <FacetGroup
        label="Severity"
        options={severities}
        selected={selectedSeverities}
        onToggle={onToggleSeverity}
      />
      <FacetGroup
        label="Status"
        options={statuses}
        selected={selectedStatuses}
        onToggle={onToggleStatus}
      />
    </div>
  );
}
