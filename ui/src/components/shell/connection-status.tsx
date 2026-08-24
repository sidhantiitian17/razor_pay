import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { isBackendConfigured, type ConnectionState } from "@/lib/backend";

const COPY: Record<ConnectionState, { label: string; dot: string; detail: string }> = {
  unconfigured: {
    label: "No data source",
    dot: "bg-muted-foreground",
    detail: "Database not enabled yet",
  },
  connecting: { label: "Connecting", dot: "bg-warning", detail: "Handshaking with data source" },
  online: { label: "Live", dot: "bg-matched", detail: "Reading via anon key under RLS" },
  offline: { label: "Offline", dot: "bg-destructive", detail: "Data source unreachable" },
};

export function useConnectionState(): ConnectionState {
  const [state, setState] = useState<ConnectionState>("unconfigured");

  useEffect(() => {
    setState(isBackendConfigured() ? "online" : "unconfigured");
  }, []);

  return state;
}

export function ConnectionStatus() {
  const state = useConnectionState();
  const copy = COPY[state];

  return (
    <div
      className="flex items-center gap-2 rounded border border-border bg-surface px-2.5 py-1.5"
      title={copy.detail}
    >
      <span className={cn("size-1.5 rounded-full", copy.dot)} aria-hidden="true" />
      <span className="label-micro text-foreground/80">{copy.label}</span>
    </div>
  );
}
