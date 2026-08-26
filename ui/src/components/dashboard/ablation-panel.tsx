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
import type { Ablation } from "@/types/report";

const ARMS: ReadonlyArray<{
  key: "rules_only" | "agent_only" | "rules_agent" | "random";
  label: string;
}> = [
  { key: "rules_only", label: "rules only" },
  { key: "agent_only", label: "agent only" },
  { key: "rules_agent", label: "rules + agent" },
  { key: "random", label: "random" },
];

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});

/** Baseline comparison: four ablation arms, plus agent lift and precision cost. */
export function AblationPanel({ ablation }: { ablation: Ablation }) {
  const rows = ARMS.map(({ key, label }) => ({
    label,
    "match rate %": ablation[key].match_rate * 100,
    "precision %": ablation[key].precision * 100,
    cost_usd: ablation[key].cost_usd,
  }));

  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="panel p-4">
        <header className="mb-3">
          <h3 className="text-sm font-semibold text-foreground">Baselines — four ablation arms</h3>
          <p className="text-xs text-muted-foreground">
            Each arm reruns the same seeded dataset with a different matcher configuration.
          </p>
        </header>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--color-grid)" vertical={false} />
              <XAxis
                dataKey="label"
                stroke="var(--color-muted-foreground)"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                stroke="var(--color-muted-foreground)"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => `${v.toFixed(0)}%`}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--color-popover)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius)",
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => [`${value.toFixed(2)}%`, name]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="match rate %" fill="var(--color-primary)" />
              <Bar dataKey="precision %" fill="var(--color-info)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <table className="mt-3 w-full border-t border-border text-xs">
          <thead>
            <tr className="text-left">
              <th className="py-1.5 font-normal">
                <span className="label-micro">Arm</span>
              </th>
              <th className="py-1.5 text-right font-normal">
                <span className="label-micro">Match rate</span>
              </th>
              <th className="py-1.5 text-right font-normal">
                <span className="label-micro">Precision</span>
              </th>
              <th className="py-1.5 text-right font-normal">
                <span className="label-micro">Cost</span>
              </th>
            </tr>
          </thead>
          <tbody className="tnum">
            {ARMS.map(({ key, label }) => (
              <tr key={key} className="border-t border-border/70">
                <td className="py-1.5 text-foreground">{label}</td>
                <td className="py-1.5 text-right text-foreground">
                  {(ablation[key].match_rate * 100).toFixed(2)}%
                </td>
                <td className="py-1.5 text-right text-foreground">
                  {(ablation[key].precision * 100).toFixed(2)}%
                </td>
                <td className="py-1.5 text-right text-foreground">
                  {usd.format(ablation[key].cost_usd)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid content-start gap-4">
        <div className="panel border-primary/40 p-4">
          <div className="label-micro">Agent lift</div>
          <div className="tnum text-2xl font-semibold text-primary">
            {(ablation.agent_lift.value * 100).toFixed(2)}%
          </div>
          <div className="tnum text-xs text-muted-foreground">
            {formatCount(ablation.agent_lift.numerator)} /{" "}
            {formatCount(ablation.agent_lift.denominator)} residuals recovered by the agent path
          </div>
        </div>

        <div className="panel border-unresolved/40 p-4">
          <div className="label-micro">Precision cost</div>
          <div className="tnum text-2xl font-semibold text-unresolved">
            {(ablation.precision_cost * 100).toFixed(2)}%
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Precision given up against rules-only to obtain that lift. Reported next to the lift,
            not netted against it.
          </p>
        </div>
      </div>
    </section>
  );
}
