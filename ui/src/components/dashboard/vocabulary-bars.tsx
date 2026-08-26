import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatCount } from "@/lib/format";
import type { ResolvedMap, UnresolvedMap } from "@/types/report";

const RESOLVED_TAGS: ReadonlyArray<{ key: keyof ResolvedMap; label: string }> = [
  { key: "clean", label: "clean" },
  { key: "drift", label: "drift" },
  { key: "timing_tolerated", label: "timing tolerated" },
  { key: "utr_recovered", label: "UTR recovered" },
  { key: "refund", label: "refund" },
];

const UNRESOLVED_BUCKETS: ReadonlyArray<{ key: keyof UnresolvedMap; label: string }> = [
  { key: "amount_mismatch", label: "amount mismatch" },
  { key: "fee_mismatch", label: "fee mismatch" },
  { key: "timing_break", label: "timing break" },
  { key: "missing_utr", label: "missing UTR" },
  { key: "duplicate", label: "duplicate" },
  { key: "refund_unpaired", label: "refund unpaired" },
  { key: "orphan_bank", label: "orphan bank" },
  { key: "orphan_ledger", label: "orphan ledger" },
  { key: "partial_group", label: "partial group" },
];

function shade(base: string, index: number, total: number): number {
  void base;
  return 1 - (index / Math.max(1, total)) * 0.6;
}

function StackedVocabularyChart({
  axisLabel,
  colorVar,
  series,
  values,
}: {
  axisLabel: string;
  colorVar: string;
  series: ReadonlyArray<{ key: string; label: string }>;
  values: Record<string, number>;
}) {
  const row: Record<string, string | number> = { name: axisLabel };
  for (const item of series) row[item.label] = values[item.key] ?? 0;

  return (
    <div className="h-72 w-full [&_.recharts-surface]:bg-transparent [&_.recharts-wrapper]:bg-transparent">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={[row]}
          layout="vertical"
          margin={{ top: 8, right: 12, bottom: 0, left: 8 }}
          className="bg-transparent"
        >
          <CartesianGrid stroke="var(--color-grid)" horizontal={false} />
          <XAxis
            type="number"
            stroke="var(--color-muted-foreground)"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => formatCount(v)}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="var(--color-muted-foreground)"
            tick={{ fontSize: 11 }}
            width={72}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-popover)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius)",
              fontSize: 12,
            }}
            formatter={(value: number, name: string) => [formatCount(value), name]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {series.map((item, index) => (
            <Bar
              key={item.key}
              dataKey={item.label}
              stackId="one"
              fill={colorVar}
              fillOpacity={shade(colorVar, index, series.length)}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function total(values: Record<string, number>, keys: ReadonlyArray<string>): number {
  return keys.reduce((sum, key) => sum + (values[key] ?? 0), 0);
}

/**
 * Resolved tags and unresolved buckets are two different vocabularies. They are
 * rendered as two separate stacked bars in two separate panels and are never
 * added together into a single total.
 */
export function VocabularyBars({
  resolved,
  unresolved,
}: {
  resolved: ResolvedMap;
  unresolved: UnresolvedMap;
}) {
  const resolvedValues: Record<string, number> = { ...resolved };
  const unresolvedValues: Record<string, number> = { ...unresolved };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="panel p-4">
        <header className="flex items-baseline justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Resolved tags</h3>
            <p className="text-xs text-muted-foreground">
              Vocabulary A — how a matched group was resolved.
            </p>
          </div>
          <span className="tnum text-sm text-matched">
            {formatCount(
              total(
                resolvedValues,
                RESOLVED_TAGS.map((t) => t.key),
              ),
            )}{" "}
            tagged
          </span>
        </header>
        <StackedVocabularyChart
          axisLabel="resolved"
          colorVar="var(--color-matched)"
          series={RESOLVED_TAGS}
          values={resolvedValues}
        />
      </section>

      <section className="panel border-unresolved/40 p-4">
        <header className="flex items-baseline justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Unresolved buckets</h3>
            <p className="text-xs text-muted-foreground">
              Vocabulary B — why an item could not be resolved. Not comparable to, and never summed
              with, the tags on the left.
            </p>
          </div>
          <span className="tnum text-sm text-unresolved">
            {formatCount(
              total(
                unresolvedValues,
                UNRESOLVED_BUCKETS.map((b) => b.key),
              ),
            )}{" "}
            bucketed
          </span>
        </header>
        <StackedVocabularyChart
          axisLabel="unresolved"
          colorVar="var(--color-unresolved)"
          series={UNRESOLVED_BUCKETS}
          values={unresolvedValues}
        />
      </section>
    </div>
  );
}

export { RESOLVED_TAGS, UNRESOLVED_BUCKETS };
