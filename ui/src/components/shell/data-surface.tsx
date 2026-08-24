import type { ReactNode } from "react";

import { EmptyState, ErrorState, PanelSkeleton } from "./page-states";

export type SurfaceStatus = "loading" | "empty" | "error" | "ready";

/**
 * Single place where a route resolves its three non-ready states, so every
 * screen renders loading / empty / error identically.
 */
export function DataSurface({
  status,
  emptyTitle,
  emptyHint,
  errorTitle,
  errorDetail,
  onRetry,
  skeletonRows,
  children,
}: {
  status: SurfaceStatus;
  emptyTitle: string;
  emptyHint: string;
  errorTitle: string;
  errorDetail: string;
  onRetry?: (() => void) | undefined;
  skeletonRows?: number | undefined;
  children?: ReactNode | undefined;
}) {
  if (status === "loading") return <PanelSkeleton rows={skeletonRows} />;
  if (status === "error")
    return <ErrorState title={errorTitle} detail={errorDetail} onRetry={onRetry} />;
  if (status === "empty") return <EmptyState title={emptyTitle} hint={emptyHint} />;
  return <>{children}</>;
}
