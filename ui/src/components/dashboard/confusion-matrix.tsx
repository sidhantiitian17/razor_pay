import { formatCount } from "@/lib/format";
import type { LinkMetrics } from "@/types/report";

/**
 * 2x2 confusion matrix for one link type. The candidate-space size is stated
 * alongside, because tn is only meaningful relative to that space.
 */
export function ConfusionMatrix({
  title,
  metrics,
  candidateSpaceSize,
}: {
  title: string;
  metrics: LinkMetrics;
  candidateSpaceSize: number;
}) {
  const cells = [
    {
      key: "tp",
      label: "TP",
      hint: "predicted link · true link",
      value: metrics.tp,
      tone: "text-matched",
    },
    {
      key: "fp",
      label: "FP",
      hint: "predicted link · no true link",
      value: metrics.fp,
      tone: "text-unresolved",
    },
    {
      key: "fn",
      label: "FN",
      hint: "no predicted link · true link",
      value: metrics.fn,
      tone: "text-unresolved",
    },
    {
      key: "tn",
      label: "TN",
      hint: "no predicted link · no true link",
      value: metrics.tn,
      tone: "text-muted-foreground",
    },
  ] as const;

  return (
    <div className="panel p-4">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <span className="tnum text-xs text-muted-foreground">
          candidate space {formatCount(candidateSpaceSize)} pairs
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        {cells.map((cell) => (
          <div key={cell.key} className="rounded border border-border bg-surface p-3">
            <div className="label-micro">{cell.label}</div>
            <div className={`tnum text-xl font-semibold ${cell.tone}`}>
              {formatCount(cell.value)}
            </div>
            <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground">{cell.hint}</p>
          </div>
        ))}
      </div>

      <dl className="mt-3 grid grid-cols-3 gap-2 border-t border-border pt-3 text-xs">
        <div>
          <dt className="label-micro">Precision</dt>
          <dd className="tnum text-foreground">
            {(metrics.precision.value * 100).toFixed(2)}%
            <span className="ml-1 text-muted-foreground">
              {formatCount(metrics.precision.numerator)} /{" "}
              {formatCount(metrics.precision.denominator)}
            </span>
          </dd>
        </div>
        <div>
          <dt className="label-micro">Recall</dt>
          <dd className="tnum text-foreground">
            {(metrics.recall.value * 100).toFixed(2)}%
            <span className="ml-1 text-muted-foreground">
              {formatCount(metrics.recall.numerator)} / {formatCount(metrics.recall.denominator)}
            </span>
          </dd>
        </div>
        <div>
          <dt className="label-micro">F1</dt>
          <dd className="tnum text-foreground">{metrics.f1.toFixed(4)}</dd>
        </div>
      </dl>
    </div>
  );
}
