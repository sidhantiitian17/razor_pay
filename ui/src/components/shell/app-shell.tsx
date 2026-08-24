import type { ReactNode } from "react";

import { ConnectionStatus } from "./connection-status";
import { RunSelector } from "./run-selector";
import { SessionBadge } from "./session-badge";
import { SidebarNav } from "./sidebar-nav";
import { ThemeToggle } from "./theme-toggle";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background">
      <SidebarNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface px-4">
          <RunSelector />
          <div className="flex items-center gap-2">
            <ConnectionStatus />
            <SessionBadge />
            <ThemeToggle />
          </div>
        </header>
        <main className="min-w-0 flex-1 p-5">{children}</main>
      </div>
    </div>
  );
}
