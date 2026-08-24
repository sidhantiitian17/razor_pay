import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shell/page-states";
import { useAuth } from "@/hooks/use-auth";
import { supabase } from "@/integrations/supabase/client";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — Settlement Reconciliation" },
      {
        name: "description",
        content:
          "Sign in to record triage decisions on settlement exceptions. Reads stay available without a session.",
      },
      { property: "og:title", content: "Sign in — Settlement Reconciliation" },
      {
        property: "og:description",
        content: "Operator sign-in for exception triage on the reconciliation control panel.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const { session, assigneeLabel } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        toast.success("Signed in");
        void navigate({ to: "/exceptions" });
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${window.location.origin}/auth` },
        });
        if (error) throw error;
        toast.success("Account created", {
          description: "Check your email if confirmation is required, then sign in.",
        });
        setMode("signin");
      }
    } catch (error) {
      toast.error(mode === "signin" ? "Sign-in failed" : "Sign-up failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    await supabase.auth.signOut();
    toast.success("Signed out");
  }

  return (
    <div className="mx-auto w-full max-w-md">
      <PageHeader
        title="Operator sign-in"
        description="Triage writes to exception status, assignee and resolution note require a session. Everything else is readable without one."
      />

      {session ? (
        <div className="panel grid gap-3 p-4">
          <div className="label-micro">Signed in</div>
          <div className="tnum text-sm text-foreground">{assigneeLabel}</div>
          <div className="flex gap-2">
            <Link
              to="/exceptions"
              className="inline-flex items-center rounded border border-border bg-surface px-3 py-1.5 text-sm text-foreground transition-colors hover:border-border-strong"
            >
              Go to workqueue
            </Link>
            <Button size="sm" variant="ghost" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="panel grid gap-3 p-4">
          <label className="grid gap-1">
            <span className="label-micro">Email</span>
            <Input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="grid gap-1">
            <span className="label-micro">Password</span>
            <Input
              type="password"
              required
              minLength={6}
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <Button type="submit" disabled={busy}>
            {mode === "signin" ? "Sign in" : "Create account"}
          </Button>
          <button
            type="button"
            className="text-xs text-muted-foreground underline-offset-2 hover:underline"
            onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
          >
            {mode === "signin" ? "Need an account? Sign up" : "Have an account? Sign in"}
          </button>
        </form>
      )}
    </div>
  );
}
