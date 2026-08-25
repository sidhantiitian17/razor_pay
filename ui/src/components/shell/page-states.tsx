import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { Database, RotateCcw, TriangleAlert } from "lucide-react";

import { usePrefersReducedMotion } from "@/hooks/use-reduced-motion";
import { Skeleton } from "@/components/ui/skeleton";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex items-end justify-between gap-4 border-b border-border pb-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-foreground">{title}</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
      </div>
      {actions}
    </div>
  );
}

/** Staged reveal for panel groups; collapses to no motion when asked. */
export function StagedReveal({ children }: { children: ReactNode }) {
  const reduced = usePrefersReducedMotion();

  return (
    <motion.div
      initial={reduced ? false : "hidden"}
      animate="shown"
      variants={{
        hidden: {},
        shown: { transition: { staggerChildren: reduced ? 0 : 0.05 } },
      }}
      className="grid gap-4"
    >
      {children}
    </motion.div>
  );
}

export function RevealItem({ children }: { children: ReactNode }) {
  const reduced = usePrefersReducedMotion();

  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: reduced ? 0 : 6 },
        shown: { opacity: 1, y: 0, transition: { duration: reduced ? 0 : 0.22 } },
      }}
    >
      {children}
    </motion.div>
  );
}

export function PanelSkeleton({ rows = 6 }: { rows?: number | undefined }) {
  return (
    <div
      className="panel p-4"
      role="status"
      aria-label="Loading data"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="mb-4 flex min-w-0 gap-3 sm:gap-6">
        <Skeleton className="h-8 w-full max-w-40" />
        <Skeleton className="h-8 w-full max-w-40" />
        <Skeleton className="h-8 w-full max-w-40" />
      </div>
      <div className="grid gap-2">
        {Array.from({ length: rows }, (_, index) => (
          <Skeleton key={index} className="h-7 w-full" />
        ))}
      </div>
      <span className="sr-only">Loading data</span>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="panel flex flex-col items-center gap-3 px-6 py-14 text-center">
      <Database className="size-5 text-muted-foreground" aria-hidden="true" />
      <div className="text-sm font-medium text-foreground">{title}</div>
      <p className="max-w-md text-sm text-muted-foreground">{hint}</p>
    </div>
  );
}

export function ErrorState({
  title,
  detail,
  onRetry,
}: {
  title: string;
  detail: string;
  onRetry?: (() => void) | undefined;
}) {
  return (
    <div
      role="alert"
      className="panel flex flex-col items-center gap-3 border-destructive/40 px-6 py-14 text-center"
    >
      <TriangleAlert className="size-5 text-destructive" aria-hidden="true" />
      <div className="text-sm font-medium text-foreground">{title}</div>
      <p className="max-w-md text-sm text-muted-foreground">{detail}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 inline-flex items-center gap-2 rounded border border-border bg-surface px-3 py-1.5 text-sm text-foreground transition-colors hover:border-border-strong"
        >
          <RotateCcw className="size-3.5" aria-hidden="true" />
          Retry
        </button>
      ) : null}
    </div>
  );
}
