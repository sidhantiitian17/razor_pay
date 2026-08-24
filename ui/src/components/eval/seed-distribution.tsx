import {
  CartesianGrid,
  Cell,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatCount } from "@/lib/format";
import { HOLDOUT_SEEDS, SEED_SETS } from "@/lib/seed-protocol";
import type { BoxStats, SeedPoint, SweepSplit } from "@/lib/use-eval-sweeps";

const pct = (value: number, digits = 2): string => `${(value * 100).toFixed(digits)}%`;

function StatLine({
  label,
  value,
  provenance,
}: {
  label: string;
  value: string;
  provenance?: string | undefined;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border/60 py-1.5 last:border-b-0">
      <span className="label-micro">{label}</span>
      <span className="tnum text-sm text-foreground">
        {value}
        {provenance ? (
          <span className="ml-2 text-xs text-muted-foreground">{provenance}</span>
        ) : null}
      </span>
    </div>
  );
}

/** Box (Q1–Q3 with whiskers and median) composed from Recharts primitives. */
function BoxPlot({ stats }: { stats: BoxStats }) {
  const pad = Math.max((stats.max - stats.min) * 0.3, 0.004);

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="var(--color-grid)" vertical={false} />
          <XAxis
            type="number"
            dataKey="x"
            domain={[0, 2]}
            ticks={[1]}
            tickFormatter={() => "holdout"}
            stroke="var(--color-muted-foreground)"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            allowDataOverflow
            domain={[stats.min - pad, stats.max + pad]}
            stroke="var(--color-muted-foreground)"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => pct(v, 1)}
          />
          <ReferenceArea
            x1={0.55}
            x2={1.45}
            y1={stats.q1}
            y2={stats.q3}
            fill="var(--color-primary)"
            fillOpacity={0.25}
            stroke="var(--color-border-strong)"
          />
          <ReferenceLine
            segment={[
              { x: 1, y: stats.min },
              { x: 1, y: stats.q1 },
            ]}
            stroke="var(--color-border-strong)"
          />
          <ReferenceLine
            segment={[
              { x: 1, y: stats.q3 },
              { x: 1, y: stats.max },
            ]}
            stroke="var(--color-border-strong)"
          />
          <ReferenceLine
            segment={[
              { x: 0.75, y: stats.min },
              { x: 1.25, y: stats.min },
            ]}
            stroke="var(--color-border-strong)"
          />
          <ReferenceLine
            segment={[
              { x: 0.75, y: stats.max },
              { x: 1.25, y: stats.max },
            ]}
            stroke="var(--color-border-strong)"
          />
          <ReferenceLine
            segment={[
              { x: 0.55, y: stats.median },
              { x: 1.45, y: stats.median },
            ]}
            stroke="var(--color-primary)"
            strokeWidth={2}
          />
          <Scatter data={[]} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

function SeedScatter({
  points,
  worstSeed,
  domain,
}: {
  points: readonly SeedPoint[];
  worstSeed: number | null;
  domain: [number, number];
}) {
  const data = points.map((point) => ({
    seed: point.seed,
    value: point.matchRate.value,
    numerator: point.matchRate.numerator,
    denominator: point.matchRate.denominator,
  }));
  const values = data.map((row) => row.value);
  const low = values.length > 0 ? Math.min(...values) : 0;
  const high = values.length > 0 ? Math.max(...values) : 1;
  const pad = Math.max((high - low) * 0.3, 0.004);

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="var(--color-grid)" />
          <XAxis
            dataKey="seed"
            type="number"
            domain={domain}
            allowDecimals={false}
            stroke="var(--color-muted-foreground)"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            dataKey="value"
            type="number"
            allowDataOverflow
            domain={[low - pad, high + pad]}
            ticks={[low - pad, low, (low + high) / 2, high, high + pad]}
            stroke="var(--color-muted-foreground)"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => pct(v, 1)}
          />

          <Tooltip
            contentStyle={{
              background: "var(--color-popover)",
              border: "1px solid var(--color-border)",
              fontSize: 12,
            }}
            formatter={(_value, _name, item) => {
              const row = item.payload as (typeof data)[number];
              return [
                `${pct(row.value)} — ${formatCount(row.numerator)} / ${formatCount(row.denominator)}`,
                `seed ${row.seed}`,
              ];
            }}
          />
          <Scatter data={data} isAnimationActive={false}>
            {data.map((row) => (
              <Cell
                key={row.seed}
                fill={row.seed === worstSeed ? "var(--color-unresolved)" : "var(--color-primary)"}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

function SeedList({
  title,
  note,
  points,
  subdued,
}: {
  title: string;
  note: string;
  points: readonly SeedPoint[];
  subdued: boolean;
}) {
  return (
    <div className={subdued ? "panel p-4 opacity-80" : "panel p-4"}>
      <header className="mb-2">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <span className="label-micro rounded border border-border px-1.5 py-0.5 text-muted-foreground">
            {note}
          </span>
        </div>
        <p className="tnum mt-1 text-xs text-muted-foreground">
          {formatCount(points.length)} seed{points.length === 1 ? "" : "s"} present
        </p>
      </header>
      {points.length === 0 ? (
        <p className="text-xs text-muted-foreground">No rows for this set.</p>
      ) : (
        <ul className="grid gap-1">
          {points.map((point) => (
            <li
              key={point.id}
              className="flex items-baseline justify-between gap-3 border-b border-border/60 py-1 text-xs last:border-b-0"
            >
              <span className="tnum text-muted-foreground">seed {point.seed}</span>
              <span className="tnum text-foreground">
                {pct(point.matchRate.value)}
                <span className="ml-2 text-muted-foreground">
                  {formatCount(point.matchRate.numerator)} /{" "}
                  {formatCount(point.matchRate.denominator)}
                </span>
              </span>
              {point.inDeclaredRange ? null : (
                <span className="label-micro rounded border border-destructive/60 px-1.5 py-0.5 text-destructive">
                  seed outside declared range
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Holdout is the claim surface: box plot + per-seed scatter with the worst seed
 * highlighted as the gate value. Dev and regression seeds are rendered apart,
 * on their own axes, labelled as not a claim.
 */
export function SeedDistribution({ split }: { split: SweepSplit }) {
  const holdout = split.points.holdout;
  const stats = split.holdoutStats;
  const worst = split.worstHoldout;
  const expected = HOLDOUT_SEEDS.length;
  const provisional = holdout.length < expected;

  return (
    <div className="grid gap-4">
      <section className="panel p-4">
        <header className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Holdout seed distribution — {SEED_SETS.holdout.claimNote}
            </h2>
            <p className="tnum mt-1 text-xs text-muted-foreground">
              seeds {SEED_SETS.holdout.range} · {formatCount(holdout.length)} of{" "}
              {formatCount(expected)} holdout seeds present
              {provisional ? " — gate value is provisional until the sweep is complete" : ""}
            </p>
          </div>
          {worst ? (
            <div className="rounded border border-unresolved/50 bg-surface px-3 py-1.5 ring-1 ring-unresolved/25">
              <div className="label-micro">Gate value — worst holdout seed</div>
              <div className="tnum text-lg font-semibold text-unresolved">
                {pct(worst.matchRate.value)}
              </div>
              <div className="tnum text-xs text-muted-foreground">
                seed {worst.seed} · {formatCount(worst.matchRate.numerator)} /{" "}
                {formatCount(worst.matchRate.denominator)} in-scope items
              </div>
            </div>
          ) : null}
        </header>

        {holdout.length === 0 || !stats ? (
          <p className="text-xs text-muted-foreground">
            No holdout sweep rows for this run, so no distribution is drawn.
          </p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)_minmax(0,1fr)]">
            <div>
              <div className="label-micro mb-1">Five-number summary</div>
              <StatLine label="max" value={pct(stats.max)} />
              <StatLine label="Q3" value={pct(stats.q3)} />
              <StatLine label="median" value={pct(stats.median)} />
              <StatLine label="Q1" value={pct(stats.q1)} />
              <StatLine
                label="min (gate)"
                value={pct(stats.min)}
                provenance={worst ? `seed ${worst.seed}` : undefined}
              />
              <StatLine label="seeds" value={formatCount(stats.count)} />
            </div>
            <BoxPlot stats={stats} />
            <SeedScatter
              points={holdout}
              worstSeed={worst?.seed ?? null}
              domain={[
                Math.min(...holdout.map((p) => p.seed)) - 1,
                Math.max(...holdout.map((p) => p.seed)) + 1,
              ]}
            />
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <SeedList
          title={`Dev seeds ${SEED_SETS.dev.range}`}
          note={SEED_SETS.dev.claimNote}
          points={split.points.dev}
          subdued
        />
        <SeedList
          title={`Regression seed ${SEED_SETS.regression.range}`}
          note={SEED_SETS.regression.claimNote}
          points={split.points.regression}
          subdued
        />
      </div>

      {split.undeclared.length > 0 || split.withoutReport.length > 0 ? (
        <section className="panel p-4">
          <h3 className="text-sm font-semibold text-foreground">Rows held out of every panel</h3>
          <ul className="mt-2 grid gap-1 text-xs text-muted-foreground">
            {split.undeclared.map((point) => (
              <li key={`undeclared-${point.id}`} className="tnum">
                seed {point.seed} — seed_set “{point.seedSet}” is not a declared set
              </li>
            ))}
            {split.withoutReport.map((row) => (
              <li key={`noreport-${row.id}`} className="tnum">
                seed {row.seed} ({row.seed_set}) — no report written yet
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
