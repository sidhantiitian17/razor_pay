import { Link } from "@tanstack/react-router";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatCount } from "@/lib/format";
import { SEED_RANGE_SUMMARY } from "@/lib/seed-protocol";
import {
  N_MAX,
  N_MIN,
  RUN_MODES,
  seedSetNote,
  validateRequest,
  type RunRequestConfig,
  type RunRequestRow,
} from "@/lib/use-run-requests";
import type { Config } from "@/types/report";

const STATUS_STYLE: Record<string, string> = {
  pending: "border-border-strong text-muted-foreground",
  claimed: "border-primary/50 text-primary",
  complete: "border-matched/50 text-matched",
  failed: "border-destructive/60 text-destructive",
};

export function RequestRunForm({
  signedIn,
  live,
  pending,
  submitError,
  rows,
  onSubmit,
}: {
  signedIn: boolean;
  live: boolean;
  pending: boolean;
  submitError: string | null;
  rows: readonly RunRequestRow[];
  onSubmit: (config: RunRequestConfig) => void;
}) {
  const [seed, setSeed] = useState("");
  const [n, setN] = useState("");
  const [mode, setMode] = useState<Config["mode"]>("rules_agent");
  const [touched, setTouched] = useState(false);

  const validation = validateRequest({ seed, n, mode });
  const note = seedSetNote(validation.seedSet);

  return (
    <section className="panel p-4">
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Request new run</h2>
          <p className="tnum mt-1 text-xs text-muted-foreground">
            Seed must fall in a declared set: {SEED_RANGE_SUMMARY}. Model, temperature, tolerances
            and guardrail thresholds are engine-owned and not submitted here.
          </p>
        </div>
        <span
          className={`label-micro rounded border px-1.5 py-0.5 ${live ? "border-matched/50 text-matched" : "border-border-strong text-muted-foreground"}`}
        >
          {live ? "status: live" : "status: polling"}
        </span>
      </header>

      {signedIn ? (
        <form
          className="grid gap-3 sm:grid-cols-[10rem_10rem_12rem_auto] sm:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            setTouched(true);
            if (validation.parsed) onSubmit(validation.parsed);
          }}
        >
          <div className="grid gap-1.5">
            <Label htmlFor="run-seed" className="label-micro">
              Seed
            </Label>
            <Input
              id="run-seed"
              inputMode="numeric"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              className="tnum"
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="run-n" className="label-micro">
              n (rows)
            </Label>
            <Input
              id="run-n"
              inputMode="numeric"
              value={n}
              onChange={(event) => setN(event.target.value)}
              className="tnum"
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="run-mode" className="label-micro">
              Mode
            </Label>
            <Select value={mode} onValueChange={(value) => setMode(value as Config["mode"])}>
              <SelectTrigger id="run-mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RUN_MODES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" disabled={pending || !validation.valid}>
            {pending ? "Submitting…" : "Request run"}
          </Button>

          <div className="sm:col-span-4">
            {note ? <p className="text-xs text-muted-foreground">{note}</p> : null}
            {touched
              ? Object.values(validation.errors).map((message) => (
                  <p key={message} className="text-xs text-destructive">
                    {message}
                  </p>
                ))
              : null}
            {submitError ? <p className="text-xs text-destructive">{submitError}</p> : null}
            <p className="tnum mt-1 text-xs text-muted-foreground">
              n accepted between {formatCount(N_MIN)} and {formatCount(N_MAX)}.
            </p>
          </div>
        </form>
      ) : (
        <div className="grid gap-2">
          <p className="text-xs text-muted-foreground">
            Submitting a run request requires a signed-in session — the anon key has no access to
            the request queue at all. Every panel above stays fully readable without signing in.
          </p>
          <Link
            to="/auth"
            className="w-fit rounded border border-border bg-surface px-3 py-1.5 text-sm text-foreground transition-colors hover:border-border-strong"
          >
            Sign in to request a run
          </Link>
        </div>
      )}

      <div className="mt-4">
        <div className="label-micro mb-1">This session’s requests</div>
        {rows.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            No requests submitted from this session yet.
          </p>
        ) : (
          <ul className="grid gap-1">
            {rows.map((row) => (
              <li
                key={row.id}
                className="flex flex-wrap items-baseline justify-between gap-3 border-b border-border/60 py-1.5 text-xs last:border-b-0"
              >
                <span className="tnum text-muted-foreground">
                  #{row.id} · seed {row.config?.seed ?? "—"} · n {row.config?.n ?? "—"} ·{" "}
                  {row.config?.mode ?? "—"}
                </span>
                <span className="tnum text-muted-foreground">
                  {row.claimed_by ? `claimed by ${row.claimed_by}` : "unclaimed"}
                  {row.claimed_at ? ` at ${row.claimed_at}` : ""}
                </span>
                <span
                  className={`label-micro rounded border px-1.5 py-0.5 ${STATUS_STYLE[row.status] ?? "border-border-strong text-muted-foreground"}`}
                >
                  {row.status}
                </span>
                {row.result_run_id ? (
                  <span className="tnum text-muted-foreground">run {row.result_run_id}</span>
                ) : null}
                {row.error_message ? (
                  <span className="tnum text-destructive">{row.error_message}</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
