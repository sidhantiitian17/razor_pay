import { useRouterState } from "@tanstack/react-router";

import { useConnectionState } from "@/components/shell/connection-status";
import type { SurfaceStatus } from "@/components/shell/data-surface";

/**
 * Resolves the state a route should render. Until the data source is enabled
 * every route is empty — no route may fabricate figures. `?state=` is an
 * inspection escape hatch for reviewing the loading and error treatments.
 */
export function useSurfaceStatus(): SurfaceStatus {
  const connection = useConnectionState();
  const search = useRouterState({ select: (state) => state.location.searchStr });

  const override = new URLSearchParams(search).get("state");
  if (override === "loading" || override === "empty" || override === "error") return override;

  if (connection === "connecting") return "loading";
  if (connection === "offline") return "error";
  return "empty";
}
