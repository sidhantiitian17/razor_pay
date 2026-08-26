import type { ReactNode } from "react";

import { AppShell } from "./app-shell";
import { RouteTransition } from "./route-transition";

export function ProductShell({ children }: { children: ReactNode }) {
  return (
    <AppShell>
      <RouteTransition>{children}</RouteTransition>
    </AppShell>
  );
}
