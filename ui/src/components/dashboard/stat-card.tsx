import type { ReactNode } from "react";

import { useCountUp } from "@/hooks/use-count-up";
import { cn } from "@/lib/utils";
import { formatCount } from "@/lib/format";
import type { MetricValue } from "@/types/report";

type Tone = "default" | "signal" | "unresolved";

const TONE_CARD: Record<Tone, string> = {
  default: "panel",
  signal: "panel border-primary/40",
  unresolved: "panel border-unresolved/50 ring-1 ring-unresolved/25",
};

const TONE_VALUE: Record<Tone, string> = {
  default: "text-foreground",
  signal: "text-primary",
  unresolved: "text-unresolved",
};

/** Institutional stat card: one figure, its provenance beneath it. */
export function StatCard({
  label,
  value,
  denominatorLine,
  note,
  badge,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  denominatorLine: string;
  note?: string | undefined;
  badge?: ReactNode | undefined;
  tone?: Tone | undefined;
}) {
  return (
    <div className={cn(TONE_CARD[tone], "flex flex-col gap-1 p-4")}>
      <div className="flex items-start justify-between gap-2">
        <span className="label-micro">{label}</span>
        {badge}
      </div>
      <div
        className={cn(
          "tnum font-semibold leading-none",
          tone === "default" ? "text-2xl" : "text-3xl",
          TONE_VALUE[tone],
        )}
      >
        {value}
      </div>
      <div className="tnum text-xs text-muted-foreground">{denominatorLine}</div>
      {note ? <p className="mt-0.5 text-xs text-muted-foreground">{note}</p> : null}
    </div>
  );
}

/** Animated numeric readout; always settles on the fetched value. */
export function CountUp({ value, format }: { value: number; format: (n: number) => string }) {
  const animated = useCountUp(value);
  return <output>{format(animated)}</output>;
}

/**
 * A rate card. The percentage is never shown without its numerator and
 * denominator, taken straight off the MetricValue.
 */
export function RateCard({
  label,
  metric,
  unitLabel,
  note,
  badge,
  tone = "default",
  digits = 2,
}: {
  label: string;
  metric: MetricValue;
  unitLabel: string;
  note?: string | undefined;
  badge?: ReactNode | undefined;
  tone?: Tone | undefined;
  digits?: number | undefined;
}) {
  return (
    <StatCard
      label={label}
      tone={tone}
      badge={badge}
      note={note}
      value={<CountUp value={metric.value * 100} format={(n) => `${n.toFixed(digits)}%`} />}
      denominatorLine={`${formatCount(metric.numerator)} / ${formatCount(metric.denominator)} ${unitLabel}`}
    />
  );
}
