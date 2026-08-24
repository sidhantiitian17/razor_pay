import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { Verdict } from "@/lib/anti-slop-checks";

const VERDICT_STYLE: Record<Verdict, string> = {
  pass: "border-matched/50 text-matched",
  fail: "border-destructive/60 text-destructive",
  vacuous: "border-border-strong text-muted-foreground",
  indeterminate: "border-border-strong text-muted-foreground",
};

const VERDICT_LABEL: Record<Verdict, string> = {
  pass: "pass",
  fail: "fail",
  vacuous: "vacuous",
  indeterminate: "not yet computable",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={cn("label-micro shrink-0 rounded border px-1.5 py-0.5", VERDICT_STYLE[verdict])}
    >
      {VERDICT_LABEL[verdict]}
    </span>
  );
}

/** A named check: its verdict and the evidence string that produced it. */
export function CheckRow({
  index,
  name,
  verdict,
  evidence,
  aside,
}: {
  index: number;
  name: string;
  verdict: Verdict;
  evidence: string;
  aside?: ReactNode | undefined;
}) {
  return (
    <li className="flex gap-3 border-b border-border/60 px-4 py-3 last:border-b-0">
      <span className="tnum w-5 shrink-0 text-xs text-muted-foreground">{index}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm font-medium text-foreground">{name}</span>
          <VerdictBadge verdict={verdict} />
        </div>
        <p className="tnum mt-1 break-words font-mono text-xs leading-relaxed text-muted-foreground">
          {evidence}
        </p>
        {aside}
      </div>
    </li>
  );
}
