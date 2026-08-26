import { Link, type LinkProps } from "@tanstack/react-router";
import { Activity, FlaskConical, Gauge, ListTree, ShieldCheck, TriangleAlert } from "lucide-react";
import type { ComponentType } from "react";

type NavRoute = {
  to: NonNullable<LinkProps["to"]>;
  label: string;
  icon: ComponentType<{ className?: string }>;
  exact: boolean;
};

const ROUTES: NavRoute[] = [
  { to: "/runs", label: "Runs", icon: ListTree, exact: true },
  { to: "/dashboard", label: "Run Dashboard", icon: Gauge, exact: false },

  { to: "/exceptions", label: "Exceptions", icon: TriangleAlert, exact: false },
  { to: "/agent-trace", label: "Agent Trace", icon: Activity, exact: false },
  { to: "/eval-lab", label: "Eval Lab", icon: FlaskConical, exact: false },
  { to: "/verify", label: "Verify", icon: ShieldCheck, exact: false },
];

export function SidebarNav() {
  return (
    <aside className="flex w-14 shrink-0 flex-col border-r border-sidebar-border bg-sidebar sm:w-56">
      <div className="flex h-14 items-center justify-center gap-2 border-b border-sidebar-border px-2 sm:justify-start sm:px-4">
        <span className="size-2 rounded-sm bg-primary text-primary-foreground" aria-hidden="true" />
        <div className="hidden leading-tight sm:block">
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
            aria-label={label}

            className="group flex items-center justify-center gap-2.5 rounded px-2 py-2 sm:justify-start sm:px-2.5 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground data-[status=active]:bg-sidebar-accent data-[status=active]:text-sidebar-accent-foreground data-[status=active]:shadow-[inset_2px_0_0_0_var(--sidebar-primary)]"
          >
            <Icon
              className="size-4 text-muted-foreground group-data-[status=active]:text-sidebar-primary"
              aria-hidden="true"
            />
            <span className="hidden sm:inline">{label}</span>
          </Link>
        ))}
      </nav>

      <div className="hidden border-t border-sidebar-border p-3 sm:block">
        <div className="label-micro">Amounts</div>
        <div className="tnum text-xs text-muted-foreground">integer paise · INR at display</div>
      </div>
    </aside>
  );
}

export const NAV_ROUTES = ROUTES;
