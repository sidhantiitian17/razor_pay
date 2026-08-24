import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AgentCallRow } from "@/lib/use-agent-calls";

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 6,
  maximumFractionDigits: 6,
});

function VerdictBadge({ verdict }: { verdict: string }) {
  return (
    <span
      className={cn(
        "label-micro rounded border px-1.5 py-0.5",
        verdict === "accepted"
          ? "border-matched/50 text-matched"
          : verdict === "rejected"
            ? "border-destructive/60 text-destructive"
            : "border-border-strong text-muted-foreground",
      )}
    >
      {verdict}
    </span>
  );
}

/** Ordered timeline of agent calls; click a row to read it verbatim. */
export function CallTimeline({
  calls,
  selectedId,
  onSelect,
}: {
  calls: AgentCallRow[];
  selectedId: string | null;
  onSelect: (call: AgentCallRow) => void;
}) {
  return (
    <div className="panel overflow-hidden">
      <div className="grid grid-cols-[3.5rem_4rem_1fr_9rem_7rem_6rem_6rem] items-center gap-2 border-b border-border bg-surface px-3 py-2">
        {["seq", "turns", "tools used", "tokens in / out", "cost", "latency", "guardrail"].map(
          (label) => (
            <span key={label} className="label-micro">
              {label}
            </span>
          ),
        )}
      </div>
      <ol className="max-h-[32rem] overflow-y-auto">
        {calls.map((call) => (
          <li key={call.call_id}>
            <button
              type="button"
              onClick={() => onSelect(call)}
              aria-current={selectedId === call.call_id}
              className={cn(
                "grid w-full grid-cols-[3.5rem_4rem_1fr_9rem_7rem_6rem_6rem] items-center gap-2 border-b border-border/60 px-3 py-2 text-left transition-colors hover:bg-accent/40",
                selectedId === call.call_id && "bg-accent/60",
              )}
            >
              <span className="tnum text-xs text-foreground">{formatCount(call.seq)}</span>
              <span className="tnum text-xs text-foreground">{formatCount(call.turns)}</span>
              <span className="truncate font-mono text-xs text-muted-foreground">
                {call.tools_used.length ? call.tools_used.join(", ") : "none recorded"}
              </span>
              <span className="tnum text-xs text-foreground">
                {formatCount(call.tokens_in)} / {formatCount(call.tokens_out)}
              </span>
              <span className="tnum text-xs text-foreground">{usd.format(call.cost_usd)}</span>
              <span className="tnum text-xs text-foreground">
                {formatCount(call.latency_ms)} ms
              </span>
              <VerdictBadge verdict={call.guardrail_verdict} />
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
