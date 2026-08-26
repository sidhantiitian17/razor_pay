import type { ReactNode } from "react";

import { ConnectionStatus } from "./connection-status";
import { RunSelector } from "./run-selector";
import { SessionBadge } from "./session-badge";
import { SidebarNav } from "./sidebar-nav";
import { ThemeToggle } from "./theme-toggle";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen w-full max-w-full overflow-x-clip bg-background">
      <SidebarNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-surface px-3 py-2 sm:h-14 sm:flex-nowrap sm:gap-4 sm:px-4 sm:py-0">
          <div className="order-2 w-full min-w-0 sm:order-1 sm:w-auto">
            <RunSelector />
          </div>
          <div className="order-1 flex min-w-0 flex-wrap items-center gap-2 sm:order-2">
            <ConnectionStatus />
            <SessionBadge />
            <ThemeToggle />
          </div>
        </header>

        <main className="min-w-0 flex-1 p-4 sm:p-5">{children}</main>
      </div>
    </div>
  );
}
