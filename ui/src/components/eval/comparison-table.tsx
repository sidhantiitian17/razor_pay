import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ComparisonResult, Direction, MetricDelta } from "@/lib/use-run-comparison";

const DIRECTION_STYLE: Record<Direction, string> = {
  improved: "text-matched",
  regressed: "text-destructive",
  unchanged: "text-muted-foreground",
  incomparable: "text-muted-foreground",
};

const DIRECTION_LABEL: Record<Direction, string> = {
  improved: "improvement",
  regressed: "regression",
  unchanged: "unchanged",
  incomparable: "not comparable",
};

function Row({ row }: { row: MetricDelta }) {
  return (
    <tr className="border-b border-border/60 last:border-b-0">
      <td className="px-3 py-2 align-top">
        <div className="text-sm text-foreground">{row.label}</div>
        <div className="label-micro text-muted-foreground">
          {row.group} · {row.polarity === "higher" ? "higher is better" : "lower is better"}
        </div>
      </td>
      <td className="tnum px-3 py-2 text-right align-top text-sm text-foreground">
        {row.formatted.a}
        {row.aProvenance ? (
          <div className="tnum text-xs text-muted-foreground">{row.aProvenance}</div>
        ) : null}
      </td>
      <td className="tnum px-3 py-2 text-right align-top text-sm text-foreground">
        {row.formatted.b}
        {row.bProvenance ? (
          <div className="tnum text-xs text-muted-foreground">{row.bProvenance}</div>
        ) : null}
      </td>
      <td
        className={cn(
          "tnum px-3 py-2 text-right align-top text-sm font-medium",
          DIRECTION_STYLE[row.direction],
        )}
      >
        {row.formatted.delta}
      </td>
      <td className="px-3 py-2 align-top">
        <span
          className={cn(
            "label-micro rounded border px-1.5 py-0.5",
            row.direction === "improved"
              ? "border-matched/50 text-matched"
              : row.direction === "regressed"
                ? "border-destructive/60 text-destructive"
                : "border-border-strong text-muted-foreground",
          )}
        >
          {DIRECTION_LABEL[row.direction]}
        </span>
        {row.note ? (
          <p className="mt-1 max-w-xs text-xs text-muted-foreground">{row.note}</p>
        ) : null}
      </td>
    </tr>
  );
}

/** Metric delta table: regressions destructive, improvements matched. */
export function ComparisonTable({
  result,
  labelA,
  labelB,
}: {
  result: ComparisonResult;
  labelA: string;
  labelB: string;
}) {
  return (
    <div className="panel overflow-hidden">
      <header className="flex flex-wrap items-baseline justify-between gap-3 border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Run comparison</h2>
        <span className="tnum text-xs text-muted-foreground">
          {formatCount(result.improved)} improved · {formatCount(result.regressed)} regressed ·{" "}
          {formatCount(result.unchanged)} unchanged / {formatCount(result.rows.length)} metrics
        </span>
      </header>

      {result.incomparableReason ? (
        <p className="border-b border-border px-4 py-2 text-xs text-destructive">
          {result.incomparableReason}
        </p>
      ) : null}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[58rem]">
          <thead>
            <tr className="border-b border-border">
              <th className="label-micro px-3 py-2 text-left">Metric</th>
              <th className="label-micro px-3 py-2 text-right">A — {labelA}</th>
              <th className="label-micro px-3 py-2 text-right">B — {labelB}</th>
              <th className="label-micro px-3 py-2 text-right">Δ (B − A)</th>
              <th className="label-micro px-3 py-2 text-left">Direction</th>
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row) => (
              <Row key={row.id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
