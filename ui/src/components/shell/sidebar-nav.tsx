import { Link, type LinkProps } from "@tanstack/react-router";
import { Activity, FlaskConical, ListTree, ShieldCheck, TriangleAlert } from "lucide-react";
import type { ComponentType } from "react";

type NavRoute = {
  to: NonNullable<LinkProps["to"]>;
  label: string;
  icon: ComponentType<{ className?: string }>;
  exact: boolean;
};

const ROUTES: NavRoute[] = [
  { to: "/", label: "Runs", icon: ListTree, exact: true },
  { to: "/exceptions", label: "Exceptions", icon: TriangleAlert, exact: false },
  { to: "/agent-trace", label: "Agent Trace", icon: Activity, exact: false },
  { to: "/eval-lab", label: "Eval Lab", icon: FlaskConical, exact: false },
  { to: "/verify", label: "Verify", icon: ShieldCheck, exact: false },
];

export function SidebarNav() {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
        <span className="size-2 rounded-sm bg-primary" aria-hidden="true" />
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight text-sidebar-foreground">RECON</div>
          <div className="label-micro">3-way settlement</div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 p-2" aria-label="Primary">
        {ROUTES.map(({ to, label, icon: Icon, exact }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact }}
            className="group flex items-center gap-2.5 rounded px-2.5 py-2 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground data-[status=active]:bg-sidebar-accent data-[status=active]:text-sidebar-accent-foreground data-[status=active]:shadow-[inset_2px_0_0_0_var(--sidebar-primary)]"
          >
            <Icon
              className="size-4 text-muted-foreground group-data-[status=active]:text-sidebar-primary"
              aria-hidden="true"
            />
            {label}
          </Link>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="label-micro">Amounts</div>
        <div className="tnum text-xs text-muted-foreground">integer paise · INR at display</div>
      </div>
    </aside>
  );
}

export const NAV_ROUTES = ROUTES;
