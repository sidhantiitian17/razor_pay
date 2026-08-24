import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { JsonViewer } from "@/components/trace/json-viewer";
import { formatCount } from "@/lib/format";
import type { AgentCallRow } from "@/lib/use-agent-calls";

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 6,
  maximumFractionDigits: 6,
});

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-surface px-2.5 py-1.5">
      <div className="label-micro">{label}</div>
      <div className="tnum text-xs text-foreground">{value}</div>
    </div>
  );
}

/** Per-call viewer: the prompt and response exactly as stored. */
export function CallSheet({ call, onClose }: { call: AgentCallRow | null; onClose: () => void }) {
  return (
    <Sheet open={Boolean(call)} onOpenChange={(open) => (open ? undefined : onClose())}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto sm:max-w-3xl">
        {call ? (
          <>
            <SheetHeader>
              <SheetTitle className="tnum text-sm">
                seq {formatCount(call.seq)} · {call.call_id}
              </SheetTitle>
              <SheetDescription>
                Prompt and response are rendered verbatim from the stored jsonb — nothing is
                reformatted or summarised.
              </SheetDescription>
            </SheetHeader>

            <div className="grid gap-3 p-4">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Fact label="Turns" value={formatCount(call.turns)} />
                <Fact
                  label="Tokens"
                  value={`${formatCount(call.tokens_in)} in / ${formatCount(call.tokens_out)} out`}
                />
                <Fact label="Cost" value={usd.format(call.cost_usd)} />
                <Fact label="Latency" value={`${formatCount(call.latency_ms)} ms`} />
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <Fact
                  label="Tools used"
                  value={call.tools_used.length ? call.tools_used.join(", ") : "none recorded"}
                />
                <Fact
                  label="Guardrail"
                  value={`${call.guardrail_verdict}${
                    call.guardrail_reasons.length ? ` — ${call.guardrail_reasons.join(", ")}` : ""
                  }`}
                />
              </div>

              <JsonViewer title="prompt_redacted" payload={call.prompt_redacted} />
              <JsonViewer title="response" payload={call.response} />
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
