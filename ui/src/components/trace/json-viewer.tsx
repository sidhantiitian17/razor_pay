import { useMemo, useState } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";

function toLines(payload: unknown): string[] {
  return JSON.stringify(payload ?? null, null, 2).split("\n");
}

/**
 * Verbatim monospace viewer with a line filter. The payload is printed exactly
 * as fetched; search only narrows which lines are shown.
 */
export function JsonViewer({ title, payload }: { title: string; payload: unknown }) {
  const [query, setQuery] = useState("");
  const lines = useMemo(() => toLines(payload), [payload]);

  const needle = query.trim().toLowerCase();
  const matches = useMemo(
    () =>
      needle
        ? lines
            .map((line, index) => ({ line, index }))
            .filter((entry) => entry.line.toLowerCase().includes(needle))
        : lines.map((line, index) => ({ line, index })),
    [lines, needle],
  );

  return (
    <div className="panel flex min-h-0 flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-border px-3 py-2">
        <span className="label-micro">{title}</span>
        <span className="tnum text-xs text-muted-foreground">
          {needle
            ? `${formatCount(matches.length)} / ${formatCount(lines.length)} lines match`
            : `${formatCount(lines.length)} lines`}
        </span>
      </div>
      <div className="border-b border-border px-3 py-2">
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`Search ${title.toLowerCase()}`}
            aria-label={`Search ${title}`}
            className="h-8 pl-7 font-mono text-xs"
          />
        </div>
      </div>
      <pre className="max-h-72 overflow-auto px-3 py-2 font-mono text-[11px] leading-relaxed text-foreground">
        {matches.map(({ line, index }) => (
          <div key={index} className="flex gap-3">
            <span className="tnum w-8 shrink-0 select-none text-right text-muted-foreground">
              {index + 1}
            </span>
            <span className={cn("whitespace-pre-wrap break-words")}>{line}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}
