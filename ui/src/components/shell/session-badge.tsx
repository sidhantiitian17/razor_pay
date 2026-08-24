import { Link } from "@tanstack/react-router";

import { useAuth } from "@/hooks/use-auth";

/** Session-driven affordance: reads work anonymously, triage needs a session. */
export function SessionBadge() {
  const { session, assigneeLabel, loading } = useAuth();

  if (loading) return null;

  return (
    <Link
      to="/auth"
      className="flex max-w-48 items-center gap-2 rounded border border-border bg-surface px-2.5 py-1.5 transition-colors hover:border-border-strong"
      title={session ? "Signed in — triage enabled" : "Sign in to triage exceptions"}
    >
      <span
        className={`size-1.5 rounded-full ${session ? "bg-matched" : "bg-muted-foreground"}`}
        aria-hidden="true"
      />
      <span className="label-micro truncate text-foreground/80">
        {session ? (assigneeLabel ?? "signed in") : "Sign in"}
      </span>
    </Link>
  );
}
