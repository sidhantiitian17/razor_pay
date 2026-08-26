import { Link, createFileRoute } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import { motion, useAnimationControls, useInView } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ArrowRight,
  Banknote,
  Braces,
  CheckCircle2,
  ChevronRight,
  Clipboard,
  Database,
  FileSearch,
  Files,
  GitBranch,
  LockKeyhole,
  RadioTower,
  RotateCcw,
  Server,
  ShieldCheck,
  TriangleAlert,
  X,
} from "lucide-react";

import agentTraceShot from "@/assets/routes/agent-trace.jpg.asset.json";
import dashboardShot from "@/assets/routes/dashboard.jpg.asset.json";
import evalLabShot from "@/assets/routes/eval-lab.jpg.asset.json";
import exceptionsShot from "@/assets/routes/exceptions.jpg.asset.json";
import runsShot from "@/assets/routes/runs.jpg.asset.json";
import verifyShot from "@/assets/routes/verify.jpg.asset.json";
import razorpayLogo from "@/assets/razorpay-logo.webp";
import runsPreview from "@/assets/runs-preview.png";
import verifyPreview from "@/assets/verify-preview.png";
import {
  ParallaxLayer,
  ParallaxScene,
  useLandingSmoothScroll,
} from "@/components/landing/parallax";
import type { SurfaceStatus } from "@/components/shell/data-surface";
import { Button } from "@/components/ui/button";

import { CoverflowCarousel, type CoverflowSlide } from "@/components/ui/coverflow-carousel";
import { Popover, PopoverClose, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

import { useAuth } from "@/hooks/use-auth";
import { usePrefersReducedMotion } from "@/hooks/use-reduced-motion";
import { formatCount } from "@/lib/format";
import { useRunCount } from "@/lib/use-run-comparison";
import { useLatestRunReport } from "@/lib/use-run-report";
import { cn } from "@/lib/utils";
import type { MetricValue, ReconciliationReport, UnresolvedMap } from "@/types/report";

const MOTION_EASE = [0.16, 1, 0.3, 1] as const;

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Settlement Sentinel — Audit-Grade Reconciliation" },
      {
        name: "description",
        content:
          "Settlement Sentinel reconciles bank statements, gateway payouts and ledger entries with deterministic rules, bounded agent review and live verification.",
      },
      { property: "og:title", content: "Settlement Sentinel — Audit-Grade Reconciliation" },
      {
        property: "og:description",
        content:
          "Institutional settlement reconciliation for bank, gateway payout and ledger operations with evidence-first exceptions and anti-slop verification.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LandingPage,
});

function unresolvedTotal(unresolved: UnresolvedMap): number {
  return Object.values(unresolved).reduce((sum, value) => sum + value, 0);
}

function percent(metric: MetricValue): string {
  return `${(metric.value * 100).toFixed(2)}%`;
}

function provenance(metric: MetricValue, label: string): string {
  return `${formatCount(metric.numerator)} / ${formatCount(metric.denominator)} ${label}`;
}

function LandingPage() {
  const reduced = usePrefersReducedMotion();
  useLandingSmoothScroll();

  const { session, loading: authLoading } = useAuth();
  const authed = Boolean(session);
  const runCount = useRunCount(authed);
  const latestRun = useLatestRunReport(authed);
  const report = latestRun.data?.report ?? null;

  const liveStatus: SurfaceStatus = authLoading
    ? "loading"
    : !authed
      ? "empty"
      : runCount.isError || latestRun.isError
        ? "error"
        : runCount.isLoading || latestRun.isLoading
          ? "loading"
          : runCount.data === 0 || !report
            ? "empty"
            : "ready";

  return (
    <main className="dark landing-trading-desk relative isolate min-h-screen overflow-hidden bg-background font-sans text-foreground">
      <LandingBackdrop />
      <LandingHeader />
      <MotionDebugLabel />

      <section className="relative border-b border-border bg-background">
        <div
          className="absolute inset-0 opacity-35 [background-image:linear-gradient(var(--grid)_1px,transparent_1px),linear-gradient(90deg,var(--grid)_1px,transparent_1px)] [background-size:44px_44px]"
          aria-hidden="true"
        />
        <div
          className="absolute inset-0 opacity-[0.08] [background-image:repeating-linear-gradient(0deg,var(--foreground)_0_1px,transparent_1px_5px)]"
          aria-hidden="true"
        />
        <div className="absolute inset-x-0 top-0 h-px bg-border-strong" aria-hidden="true" />
        <div className="relative mx-auto grid w-full max-w-7xl gap-12 px-4 py-10 sm:px-6 lg:px-8">
          <ParallaxScene className="grid gap-12" probe="hero-parallax">
            <ParallaxLayer layer="4">
              <motion.div
                data-motion-probe="hero-layout"
                initial={reduced ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reduced ? 0 : 0.28, ease: MOTION_EASE }}
                className="grid items-center gap-10 pt-6 lg:grid-cols-[0.86fr_1.14fr] lg:pt-12"
              >
                <div className="min-w-0 rounded-md border border-border-strong border-l-primary bg-background p-4 sm:p-5">
                  <div className="label-micro mb-4 inline-flex rounded-sm border border-primary/30 bg-surface px-2 py-1">
                    Settlement ops console · bank / payout / ledger
                  </div>
                  <h1 className="max-w-4xl font-mono text-4xl font-semibold leading-tight text-foreground sm:text-6xl lg:text-7xl">
                    Settlement Sentinel / RECON
                  </h1>
                  <p className="mt-5 max-w-3xl text-xl font-medium text-foreground sm:text-2xl">
                    A control plane for settlement breaks before they become finance risk.
                  </p>
                  <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
                    Bank statement, gateway payout and general ledger records are reconciled through
                    deterministic rules plus a bounded LLM agent, with evidence-first exceptions,
                    reversible closures and verification that refuses fabricated certainty.
                  </p>
                  <div className="mt-6 grid gap-2 border-y border-border py-3 sm:grid-cols-3">
                    {[
                      ["bank rail", "BNK- rows"],
                      ["gateway rail", "pout_SYNTH rows"],
                      ["ledger rail", "LED- rows"],
                    ].map(([label, value]) => (
                      <div
                        key={label}
                        className="rounded-sm border border-border bg-card/70 px-3 py-2"
                      >
                        <div className="label-micro">{label}</div>
                        <div className="tnum mt-1 text-xs text-foreground">{value}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                    <TapTarget glow className="w-full sm:w-auto">
                      <Button
                        asChild
                        size="lg"
                        className="w-full border border-primary/40 font-mono shadow-none transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 sm:w-auto"
                      >
                        <Link to={authed ? "/runs" : "/auth"}>
                          Enter app
                          <ArrowRight aria-hidden="true" />
                        </Link>
                      </Button>
                    </TapTarget>
                    <TapTarget className="w-full sm:w-auto">
                      <Button
                        asChild
                        size="lg"
                        variant="outline"
                        className="w-full bg-surface font-mono shadow-none sm:w-auto"
                      >
                        <a href="#proof">Review verification</a>
                      </Button>
                    </TapTarget>
                  </div>
                </div>

                <HeroProductFrame reduced={reduced} />
              </motion.div>
            </ParallaxLayer>

            <ParallaxLayer layer="3">
              <motion.div
                initial={reduced ? false : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: reduced ? 0 : 0.3,
                  delay: reduced ? 0 : 0.08,
                  ease: MOTION_EASE,
                }}
                className="mt-12"
              >
                <LiveStatsBar
                  locked={!authed && !authLoading}
                  status={liveStatus}
                  runCount={runCount.data}
                  report={report}
                  onRetry={() => {
                    void runCount.refetch();
                    void latestRun.refetch();
                  }}
                />
              </motion.div>
            </ParallaxLayer>
          </ParallaxScene>
        </div>
      </section>

      <ReconciliationParallaxScene />
      <ProblemSolution report={report} />
      <ConsoleShowcase />

      <FeatureGrid report={report} />
      <HowItWorks />
      <GettingStarted />
      <ProductPreview />
      <LandingFooter />
    </main>
  );
}

/**
 * Landing-only decorative backdrop: a visible pixel grid plus soft violet
 * radial light, both built from the landing theme tokens. Fixed, aria-hidden and
 * pointer-events-none; the restrained opacity keeps content contrast intact.
 */
function LandingBackdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
      {/* Faint pixel grid beneath the glow. */}
      <div className="absolute inset-0 opacity-[0.5] [background-image:linear-gradient(var(--grid)_1px,transparent_1px),linear-gradient(90deg,var(--grid)_1px,transparent_1px)] [background-size:32px_32px]" />
      {/* One soft, centered, evenly-diffused violet glow that feathers out
          toward the edges — single well-blended radial, dark palette kept. */}
      <div
        className="absolute left-1/2 top-1/2 h-[160vh] w-[160vw] -translate-x-1/2 -translate-y-1/2 opacity-[0.5]"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, color-mix(in oklab, var(--primary) 50%, transparent) 0%, color-mix(in oklab, var(--primary) 34%, transparent) 28%, color-mix(in oklab, var(--primary) 18%, transparent) 52%, color-mix(in oklab, var(--primary) 6%, transparent) 70%, transparent 85%)",
        }}
      />
    </div>
  );
}

function ReconciliationParallaxScene() {
  const reduced = usePrefersReducedMotion();

  return (
    <section
      className="relative isolate min-h-[82svh] overflow-hidden border-b border-border bg-background"
      aria-labelledby="recon-scene-title"
    >
      <ParallaxScene
        probe="reconciliation-visual-parallax"
        className="mx-auto min-h-[82svh] w-full max-w-[100rem]"
      >
        <ParallaxLayer layer="4" className="absolute inset-[-12%]">
          <div
            className="absolute inset-0 opacity-70 [background-image:linear-gradient(var(--grid)_1px,transparent_1px),linear-gradient(90deg,var(--grid)_1px,transparent_1px)] [background-size:40px_40px]"
            aria-hidden="true"
          />
          <div
            className="absolute inset-0 opacity-50 [background-image:radial-gradient(var(--border-strong)_1px,transparent_1px)] [background-size:10px_10px]"
            aria-hidden="true"
          />
          <div className="absolute inset-x-0 top-1/2 h-px bg-border-strong" aria-hidden="true" />
          <div className="absolute inset-y-0 left-1/2 w-px bg-border-strong" aria-hidden="true" />
        </ParallaxLayer>

        <ParallaxLayer layer="3" className="absolute inset-0">
          <div className="absolute inset-x-4 top-1/2 mx-auto h-[28rem] max-w-6xl -translate-y-1/2 sm:inset-x-8 sm:h-[34rem]">
            <svg
              viewBox="0 0 1200 560"
              className="absolute inset-0 size-full text-border-strong"
              aria-hidden="true"
              preserveAspectRatio="none"
            >
              <path
                d="M136 116 C360 116 404 280 600 280"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                d="M1064 116 C840 116 796 280 600 280"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                d="M600 280 C600 374 600 410 600 470"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                d="M136 116 H1064"
                fill="none"
                stroke="var(--grid)"
                strokeWidth="1"
                strokeDasharray="8 12"
              />
            </svg>

            <RailNode
              className="left-[2%] top-[4%]"
              icon={Banknote}
              label="BANK"
              tone="text-info"
            />
            <RailNode
              className="right-[2%] top-[4%]"
              icon={Server}
              label="GATEWAY"
              tone="text-warning"
            />
            <RailNode
              className="bottom-[1%] left-1/2 -translate-x-1/2"
              icon={Files}
              label="LEDGER"
              tone="text-matched"
            />
            <RailNode
              className="left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
              icon={GitBranch}
              label="RECONCILE"
              tone="text-primary"
              primary
            />
          </div>
        </ParallaxLayer>

        <ParallaxLayer layer="2" className="absolute inset-0">
          <svg
            viewBox="0 0 1200 560"
            className="absolute left-1/2 top-1/2 h-[28rem] w-[calc(100%-2rem)] max-w-6xl -translate-x-1/2 -translate-y-1/2 overflow-visible sm:h-[34rem] sm:w-[calc(100%-4rem)]"
            aria-hidden="true"
            preserveAspectRatio="none"
          >
            {reduced ? (
              <>
                <circle cx="600" cy="280" r="6" className="fill-info" />
                <circle cx="600" cy="280" r="6" className="fill-warning" />
                <circle cx="600" cy="280" r="6" className="fill-matched" />
              </>
            ) : (
              <>
                <SceneFlowParticle
                  path="M136 116 C360 116 404 280 600 280"
                  tone="info"
                  duration="3.2s"
                  begin="0s"
                />
                <SceneFlowParticle
                  path="M1064 116 C840 116 796 280 600 280"
                  tone="warning"
                  duration="3.6s"
                  begin="0.45s"
                />
                <SceneFlowParticle
                  path="M600 470 C600 374 600 330 600 280"
                  tone="matched"
                  duration="2.8s"
                  begin="0.9s"
                />
              </>
            )}
          </svg>
        </ParallaxLayer>

        <ParallaxLayer layer="1" className="absolute inset-0 z-10 grid place-items-center px-4">
          <h2
            id="recon-scene-title"
            className="max-w-[12ch] text-center font-mono text-[clamp(3.25rem,11vw,10rem)] font-semibold leading-[0.82] text-foreground/95 [text-shadow:0_2px_28px_var(--background)]"
          >
            THREE RAILS.
            <br />
            ONE TRUTH.
          </h2>
        </ParallaxLayer>
      </ParallaxScene>
    </section>
  );
}

function SceneFlowParticle({
  path,
  tone,
  duration,
  begin,
}: {
  path: string;
  tone: "info" | "warning" | "matched";
  duration: string;
  begin: string;
}) {
  const fillClass =
    tone === "info" ? "fill-info" : tone === "warning" ? "fill-warning" : "fill-matched";

  return (
    <circle data-hero-particle="true" cx="0" cy="0" r="6" className={fillClass}>
      <animateMotion path={path} dur={duration} begin={begin} repeatCount="indefinite" />
    </circle>
  );
}

function RailNode({
  className,
  icon: Icon,
  label,
  tone,
  primary = false,
}: {
  className: string;
  icon: LucideIcon;
  label: string;
  tone: string;
  primary?: boolean | undefined;
}) {
  return (
    <div
      className={cn(
        "absolute grid min-w-24 place-items-center gap-2 border border-border-strong bg-card/90 px-4 py-3 font-mono shadow-2xl backdrop-blur-sm sm:min-w-32 sm:px-6 sm:py-4",
        primary && "border-primary/70 bg-background/95",
        tone,
        className,
      )}
    >
      <Icon className={cn(primary ? "size-8 sm:size-10" : "size-6 sm:size-8")} aria-hidden="true" />
      <span className="text-[10px] font-semibold tracking-widest sm:text-xs">{label}</span>
    </div>
  );
}

function LandingHeader() {
  const { session } = useAuth();
  const authed = Boolean(session);

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/90 font-mono backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className="flex min-w-0 items-center gap-3"
          aria-label="Settlement Sentinel home"
        >
          <span className="flex shrink-0 items-center rounded border border-primary/50 bg-foreground px-1.5 py-1">
            <img src={razorpayLogo} alt="Razorpay" className="h-4 w-auto" />
          </span>

          <span className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold text-foreground">
              Settlement Sentinel
            </span>
            <span className="label-micro block truncate">RECON control plane</span>
          </span>
        </Link>
        <nav className="flex shrink-0 items-center gap-2" aria-label="Landing">
          <TapTarget>
            <Button
              asChild
              variant="ghost"
              size="sm"
              title="Every reconciliation surface requires an operator session."
            >
              <Link
                to="/auth"
                aria-label={
                  authed
                    ? "Manage operator session"
                    : "Operator sign-in; every reconciliation surface requires a session"
                }
              >
                <span className="hidden sm:inline">
                  {authed ? "Operator session" : "Operator sign-in"}
                </span>
                <span className="sm:hidden">Operator</span>
              </Link>
            </Button>
          </TapTarget>
          <TapTarget glow>
            <Button asChild size="sm">
              <Link to={authed ? "/runs" : "/auth"}>Enter app</Link>
            </Button>
          </TapTarget>
        </nav>
      </div>
    </header>
  );
}

function MotionDebugLabel() {
  const reduced = usePrefersReducedMotion();

  return (
    <div
      className="pointer-events-none fixed bottom-3 right-3 z-[80] rounded border border-primary/60 bg-background/95 px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wider text-primary shadow-lg backdrop-blur"
      aria-hidden="true"
    >
      motion: {reduced ? "reduced" : "normal"}
    </div>
  );
}

/**
 * Click feedback shared by every landing control: a quick scale-down-then-settle
 * plus (on primary CTAs) a ring pulse. Reduced motion keeps the state change
 * instant and skips both.
 */
function usePressPulse(reduced: boolean) {
  const controls = useAnimationControls();
  const [pulsing, setPulsing] = useState(false);

  const trigger = () => {
    setPulsing(true);
    window.setTimeout(() => setPulsing(false), 320);
    if (reduced) return;
    void controls.start(
      { scale: [1, 0.96, 1] },
      { duration: 0.15, ease: "easeOut", times: [0, 0.45, 1] },
    );
  };

  return { controls, pulsing, trigger };
}

function TapTarget({
  children,
  className,
  glow,
}: {
  children: ReactNode;
  className?: string | undefined;
  glow?: boolean | undefined;
}) {
  const reduced = usePrefersReducedMotion();
  const { controls, pulsing, trigger } = usePressPulse(reduced);

  return (
    <motion.span
      data-tap-target="true"
      data-tap-glow={glow ? "true" : undefined}
      data-pressed={pulsing ? "true" : undefined}
      animate={controls}
      className={cn("inline-block origin-center rounded-md", className)}
      onPointerDown={trigger}
    >
      {children}
    </motion.span>
  );
}

function LiveStatsBar({
  status,
  locked,
  runCount,
  report,
  onRetry,
}: {
  status: SurfaceStatus;
  locked: boolean;
  runCount: number | undefined;
  report: ReconciliationReport | null;
  onRetry: () => void;
}) {
  const reduced = usePrefersReducedMotion();
  return (
    <section
      aria-labelledby="live-stats-title"
      className="rounded-md border border-primary/20 bg-card/90 p-3 backdrop-blur"
    >
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3 px-1">
        <h2
          id="live-stats-title"
          className="flex items-center gap-2 font-mono text-sm font-semibold text-foreground"
        >
          <LiveDot reduced={reduced} />
          Live run signal
        </h2>
        {report ? (
          <span className="tnum text-xs text-muted-foreground">
            latest seed {formatCount(report.config.seed)} · {report.config.seed_set} ·{" "}
            {report.engine_version}
          </span>
        ) : null}
      </div>
      {status === "loading" ? <LandingLiveStatsFallback state="loading" /> : null}
      {status === "error" ? <LandingLiveStatsFallback state="error" onRetry={onRetry} /> : null}
      {status === "empty" ? (
        <LandingLiveStatsFallback
          state="empty"
          title={
            locked ? "Sign in to read live run statistics" : "No live run statistics available"
          }
          hint={
            locked
              ? "Reconciliation data is restricted to authenticated operators at the database level, so no figure is rendered here without a session."
              : "The landing page withholds metric tiles until the runs table contains a report with real values."
          }
        />
      ) : null}
      {status === "ready" && report && typeof runCount === "number" ? (
        <div className="grid gap-2 md:grid-cols-3">
          <LiveStatTile
            label="Published runs"
            value={runCount}
            formatValue={formatCount}
            detail="Exact count from the runs table."
          />
          <LiveStatTile
            label="Latest match rate"
            value={report.accuracy.match_rate.value * 100}
            formatValue={(value) => `${value.toFixed(2)}%`}
            detail={provenance(report.accuracy.match_rate, "in-scope items")}
          />
          <LiveStatTile
            prominent
            label="Latest unresolved rate"
            value={report.accuracy.unresolved_rate.value * 100}
            formatValue={(value) => `${value.toFixed(2)}%`}
            detail={`${provenance(report.accuracy.unresolved_rate, "in-scope items")} · ${formatCount(unresolvedTotal(report.unresolved))} unresolved bucketed`}
          />
        </div>
      ) : null}
    </section>
  );
}

function LandingLiveStatsFallback({
  state,
  title,
  hint,
  onRetry,
}: {
  state: "loading" | "empty" | "error";
  title?: string | undefined;
  hint?: string | undefined;
  onRetry?: (() => void) | undefined;
}) {
  const isError = state === "error";
  const Icon = isError ? TriangleAlert : Database;

  return (
    <div
      role={state === "loading" ? "status" : isError ? "alert" : undefined}
      aria-busy={state === "loading" ? "true" : undefined}
      className={cn(
        "grid min-h-36 place-items-center rounded-md border bg-background/70 p-6 text-center",
        isError ? "border-destructive/50" : "border-border",
      )}
    >
      {state === "loading" ? (
        <div className="grid w-full max-w-3xl gap-2" aria-label="Loading live run statistics">
          <div className="h-6 rounded border border-border bg-surface" />
          <div className="h-6 rounded border border-border bg-surface" />
          <div className="h-6 rounded border border-border bg-surface" />
        </div>
      ) : (
        <div className="max-w-md">
          <Icon
            className={cn("mx-auto size-5", isError ? "text-destructive" : "text-muted-foreground")}
            aria-hidden="true"
          />
          <div className="mt-3 text-sm font-medium text-foreground">
            {isError ? "Live statistics unavailable" : title}
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {isError
              ? "The run queries failed, so no marketing statistic is rendered from stale or synthetic data."
              : hint}
          </p>
          {isError && onRetry ? (
            <Button type="button" variant="outline" size="sm" className="mt-4" onClick={onRetry}>
              <RotateCcw className="size-3.5" aria-hidden="true" />
              Retry
            </Button>
          ) : null}
        </div>
      )}
    </div>
  );
}

function LiveDot({ reduced }: { reduced: boolean }) {
  return (
    <span className="relative flex size-2" aria-hidden="true">
      {reduced ? null : (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-matched opacity-75" />
      )}
      <span className="relative inline-flex size-2 rounded-full bg-matched" />
    </span>
  );
}

function LiveStatTile({
  label,
  value,
  formatValue,
  detail,
  prominent,
}: {
  label: string;
  value: number;
  formatValue: (value: number) => string;
  detail: string;
  prominent?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduced = usePrefersReducedMotion();
  const displayedValue = useCountUpOnView(value, inView, reduced);

  return (
    <motion.div
      ref={ref}
      initial={reduced ? false : { opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: reduced ? 0 : 0.28, ease: MOTION_EASE }}
      className={cn(
        "rounded-md border border-border bg-surface/70 p-4 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:border-primary/40",
        prominent && "border-unresolved/60 bg-card",
      )}
    >
      <div className="label-micro">{label}</div>
      <div
        className={cn(
          "tnum mt-2 text-3xl font-semibold",
          prominent ? "text-unresolved" : "text-foreground",
        )}
      >
        <output aria-label={formatValue(value)}>{formatValue(displayedValue)}</output>
      </div>
      <p className="tnum mt-2 text-xs text-muted-foreground">{detail}</p>
    </motion.div>
  );
}

function useCountUpOnView(target: number, active: boolean, reduced: boolean): number {
  const [value, setValue] = useState(0);
  const animated = useRef(false);

  useEffect(() => {
    if (reduced) {
      animated.current = true;
      setValue(target);
      return;
    }

    if (!active) {
      setValue(0);
      return;
    }

    if (animated.current) {
      setValue(target);
      return;
    }

    animated.current = true;
    let frame = 0;
    const start = performance.now();
    const durationMs = 380;

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);

      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      } else {
        setValue(target);
      }
    };

    setValue(0);
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [active, reduced, target]);

  return value;
}

function SectionReveal({
  children,
  className,
  dataProbe,
}: {
  children: ReactNode;
  className?: string | undefined;
  dataProbe?: string | undefined;
}) {
  const reduced = usePrefersReducedMotion();

  if (reduced) {
    return (
      <div className={className} data-motion-probe={dataProbe}>
        {children}
      </div>
    );
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px", amount: 0.01 }}
      transition={{ duration: 0.34, ease: MOTION_EASE }}
      className={className}
      data-motion-probe={dataProbe}
    >
      {children}
    </motion.div>
  );
}

function HeroProductFrame({ reduced }: { reduced: boolean }) {
  return (
    <motion.div
      data-motion-probe="hero-frame"
      initial={reduced ? false : { opacity: 0, y: 14, scale: 0.98, rotate: -1.5 }}
      animate={{ opacity: 1, y: 0, scale: 1, rotate: -1.5 }}
      transition={{ duration: reduced ? 0 : 0.34, ease: MOTION_EASE, delay: reduced ? 0 : 0.12 }}
      className="relative min-w-0 lg:translate-x-4"
    >
      <HeroArchitectureDiagram reduced={reduced} />
      <BrowserFrame
        image={runsPreview}
        alt="Real Runs dashboard showing selected reconciliation run metrics inside the app shell"
        title="Runs · live control panel"
        href="/runs"
        className="relative shadow-2xl"
      />
      <div className="absolute -bottom-5 left-4 hidden rounded-sm border border-primary/30 bg-card/95 px-3 py-2 backdrop-blur sm:block">
        <div className="label-micro">selection state</div>
        <div className="tnum mt-1 text-xs text-foreground">
          header run selector drives every surface
        </div>
      </div>
    </motion.div>
  );
}

function HeroArchitectureDiagram({ reduced }: { reduced: boolean }) {
  const [activeStage, setActiveStage] = useState<string | null>(null);

  return (
    <div
      data-hero-diagram="true"
      className="pointer-events-none absolute -inset-x-4 -top-8 bottom-10 z-30 overflow-hidden rounded-[2rem]"
      aria-label="Three-way reconciliation architecture"
    >
      <svg
        viewBox="0 0 320 236"
        className="absolute inset-0 h-full w-full"
        role="presentation"
        aria-hidden="true"
      >
        <defs>
          <marker id="hero-flow-marker" markerWidth="6" markerHeight="6" refX="3" refY="3">
            <circle cx="3" cy="3" r="1.5" className="fill-primary" />
          </marker>
        </defs>
        <DiagramPath
          id="hero-bank-flow-mask"
          d="M48 62 C78 66 102 88 134 108"
          strokeClassName="stroke-primary/70"
          delay={0.34}
          reduced={reduced}
        />
        <DiagramPath
          id="hero-ledger-flow-mask"
          d="M52 178 C82 166 108 144 134 126"
          strokeClassName="stroke-info/70"
          delay={0.4}
          reduced={reduced}
        />
        <DiagramPath
          id="hero-evidence-flow-mask"
          d="M180 118 C210 118 238 118 266 118"
          strokeClassName="stroke-warning/70"
          delay={0.46}
          reduced={reduced}
        />
        {reduced ? null : (
          <>
            <FlowParticle
              x={[48, 78, 102, 134]}
              y={[62, 66, 88, 108]}
              delay={0.78}
              tone="primary"
            />
            <FlowParticle
              x={[44, 74, 100, 134]}
              y={[66, 70, 90, 110]}
              delay={1.18}
              tone="primary"
            />
            <FlowParticle
              x={[52, 82, 108, 134]}
              y={[178, 166, 144, 126]}
              delay={0.96}
              tone="info"
            />
            <FlowParticle
              x={[56, 86, 112, 136]}
              y={[172, 162, 142, 124]}
              delay={1.36}
              tone="info"
            />
            <FlowParticle
              x={[180, 210, 238, 266]}
              y={[118, 118, 118, 118]}
              delay={2.34}
              tone="warning"
            />
            <FlowParticle
              x={[184, 214, 242, 270]}
              y={[122, 122, 122, 122]}
              delay={2.74}
              tone="warning"
            />
          </>
        )}
      </svg>

      <DiagramNode
        className="left-[5%] top-[19%]"
        label="Bank rail"
        detail="Bank statement rows enter as BNK- records and stay traceable through matching."
        icon={Banknote}
        tone="primary"
        side="left"
        active={activeStage === "bank"}
        onOpenChange={(open) => setActiveStage(open ? "bank" : null)}
      />
      <DiagramNode
        className="left-[7%] bottom-[17%]"
        label="Ledger rail"
        detail="Ledger rows enter as LED- records so the book side remains separate from payout data."
        icon={Server}
        tone="info"
        side="left"
        active={activeStage === "ledger"}
        onOpenChange={(open) => setActiveStage(open ? "ledger" : null)}
      />
      <DiagramNode
        className="left-[43%] top-[43%]"
        label="Reconciliation agent"
        detail="Rules converge first; bounded agent review handles residual breaks with evidence."
        icon={GitBranch}
        tone="primary"
        strong
        side="top"
        active={activeStage === "agent"}
        onOpenChange={(open) => setActiveStage(open ? "agent" : null)}
      />
      <DiagramNode
        className="right-[4%] top-[43%]"
        label="Evidence output"
        detail="Exceptions flow out with source links, matched fields, deltas and proposed action."
        icon={Files}
        tone="warning"
        side="right"
        active={activeStage === "evidence"}
        onOpenChange={(open) => setActiveStage(open ? "evidence" : null)}
      />
    </div>
  );
}

function DiagramPath({
  id,
  d,
  strokeClassName,
  delay,
  reduced,
}: {
  id: string;
  d: string;
  strokeClassName: string;
  delay: number;
  reduced: boolean;
}) {
  return (
    <>
      {reduced ? null : (
        <mask id={id} maskUnits="userSpaceOnUse">
          <motion.path
            d={d}
            fill="none"
            stroke="white"
            strokeWidth="5"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.34, delay, ease: MOTION_EASE }}
          />
        </mask>
      )}
      <path
        d={d}
        className={strokeClassName}
        fill="none"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeDasharray="2 8"
        mask={reduced ? undefined : `url(#${id})`}
      />
    </>
  );
}

function FlowParticle({
  x,
  y,
  delay,
  tone,
}: {
  x: number[];
  y: number[];
  delay: number;
  tone: "primary" | "info" | "warning";
}) {
  const fillClass =
    tone === "primary" ? "fill-primary" : tone === "info" ? "fill-info" : "fill-warning";
  const startX = x[0] ?? 0;
  const startY = y[0] ?? 0;

  return (
    <motion.g
      data-hero-particle="true"
      initial={{ opacity: 0 }}
      animate={{
        x: x.map((value) => value - startX),
        y: y.map((value) => value - startY),
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 3.6,
        delay,
        repeat: Infinity,
        ease: "linear",
        times: [0, 0.16, 0.84, 1],
      }}
    >
      <circle cx={startX} cy={startY} r="3.4" className={fillClass} />
    </motion.g>
  );
}

function DiagramNode({
  className,
  label,
  icon: Icon,
  tone,
  strong,
  detail,
  active,
  onOpenChange,
  side,
}: {
  className: string;
  label: string;
  icon: LucideIcon;
  tone: "primary" | "info" | "warning";
  strong?: boolean;
  detail: string;
  active: boolean;
  onOpenChange: (open: boolean) => void;
  side: "top" | "right" | "bottom" | "left";
}) {
  const reduced = usePrefersReducedMotion();
  const toneClass =
    tone === "primary"
      ? "border-primary/60 text-primary"
      : tone === "info"
        ? "border-info/60 text-info"
        : "border-warning/60 text-warning";
  const tooltipId = `diagram-${label.toLowerCase().replace(/[^a-z]+/g, "-")}`;
  const { controls, pulsing, trigger } = usePressPulse(reduced);

  return (
    <Popover open={active} onOpenChange={onOpenChange}>
      <motion.div
        data-diagram-node="true"
        data-pressed={pulsing ? "true" : undefined}
        animate={controls}
        className={cn("pointer-events-auto absolute origin-center", className)}
        onPointerDown={trigger}
      >
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-expanded={active}
            aria-describedby={active ? tooltipId : undefined}
            className={cn(
              "grid size-14 place-items-center rounded-md border bg-card/95 p-0 shadow-none backdrop-blur-sm transition-colors hover:bg-background",
              strong && "size-16 bg-background",
              active && "bg-background ring-1 ring-primary/50",
              toneClass,
            )}
          >
            <Icon className={cn(strong ? "size-6" : "size-5")} aria-hidden="true" />
            <span className="sr-only">{label}</span>
          </Button>
        </PopoverTrigger>
      </motion.div>
      <PopoverContent
        id={tooltipId}
        side={side}
        align="center"
        sideOffset={10}
        collisionPadding={24}
        avoidCollisions
        className="landing-popover-surface z-[90] w-[min(18rem,calc(100vw-2rem))] border-border-strong bg-background/95 p-3 pr-9 text-left shadow-2xl backdrop-blur"
      >
        <div className="label-micro">{label}</div>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
        <PopoverClose asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => onOpenChange(false)}
            className="absolute right-1.5 top-1.5 size-7 text-muted-foreground hover:text-foreground"
            aria-label={`Close ${label} detail`}
          >
            <X className="size-3.5" aria-hidden="true" />
          </Button>
        </PopoverClose>
      </PopoverContent>
    </Popover>
  );
}

function BrowserFrame({
  image,
  alt,
  title,
  href,
  className,
}: {
  image: string;
  alt: string;
  title: string;
  href: string;
  className?: string | undefined;
}) {
  return (
    <figure
      className={cn("overflow-hidden rounded-md border border-border-strong bg-card", className)}
    >
      <div className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2">
        <span className="size-2.5 rounded-full bg-destructive" aria-hidden="true" />
        <span className="size-2.5 rounded-full bg-warning" aria-hidden="true" />
        <span className="size-2.5 rounded-full bg-matched" aria-hidden="true" />
        <div className="tnum ml-2 min-w-0 flex-1 truncate rounded border border-border bg-background px-2 py-1 text-xs text-muted-foreground">
          {href}
        </div>
      </div>
      <img
        src={image}
        width={1280}
        height={900}
        alt={alt}
        className="block w-full"
        loading="lazy"
      />
      <figcaption className="flex items-center justify-between gap-3 border-t border-border bg-surface/80 px-3 py-2 font-mono text-xs text-muted-foreground">
        <span>{title}</span>
        <span className="label-micro">actual UI</span>
      </figcaption>
    </figure>
  );
}

type FeatureAccent = "primary" | "warning" | "violet" | "sky";

const FEATURES: Array<{
  title: string;
  body: string;
  icon: LucideIcon;
  size: string;
  visual: "match" | "trace" | "verify" | "realtime";
  accent: FeatureAccent;
}> = [
  {
    title: "Rules plus bounded agent review",
    body: "Deterministic matching handles the clean path while the agent path is constrained to residuals, evidence and guardrail verdicts.",
    icon: GitBranch,
    size: "lg:col-span-2",
    visual: "match",
    accent: "primary",
  },
  {
    title: "Audit-grade closures",
    body: "Closures are reported with reversibility, idempotence checks and second-pass closure evidence instead of silent mutation.",
    icon: LockKeyhole,
    size: "",
    visual: "trace",
    accent: "warning",
  },
  {
    title: "Anti-slop verification",
    body: "The Verify surface derives checks from fetched rows and prints the evidence behind each verdict, including negative controls.",
    icon: ShieldCheck,
    size: "",
    visual: "verify",
    accent: "violet",
  },
  {
    title: "Holdout-gated evaluation",
    body: "Eval Lab separates dev tuning from holdout claims and treats the worst holdout seed as the gate value.",
    icon: FileSearch,
    size: "lg:col-span-2",
    visual: "realtime",
    accent: "sky",
  },
];

const PROBLEM_SOLUTION_STEPS: Array<{
  eyebrow: string;
  title: string;
  detail: string;
  icon: LucideIcon;
  accent: "risk" | "warning" | "primary";
}> = [
  {
    eyebrow: "The Problem",
    title: "Money gets split across systems.",
    detail:
      "Bank, gateway and ledger records do not automatically agree, so mismatches can hide finance and compliance risk.",
    icon: TriangleAlert,
    accent: "risk",
  },
  {
    eyebrow: "How It Works",
    title: "Rules match first; AI only reviews the leftovers.",
    detail:
      "Obvious matches close deterministically, unclear breaks get bounded review, and every decision keeps its evidence.",
    icon: GitBranch,
    accent: "warning",
  },
  {
    eyebrow: "The Result",
    title: "The leftovers stay visible.",
    detail:
      "Matched items close automatically while unresolved items remain tracked, counted and available for operator review.",
    icon: CheckCircle2,
    accent: "primary",
  },
];

function ProblemSolution({ report }: { report: ReconciliationReport | null }) {
  return (
    <section className="border-b border-border bg-background py-24" aria-labelledby="plain-title">
      <SectionReveal dataProbe="plain-section" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ParallaxScene probe="plain-parallax">
          <ParallaxLayer layer="4" className="max-w-3xl">
            <div className="label-micro mb-3">Plain-language tour</div>
            <h2
              id="plain-title"
              className="font-mono text-3xl font-semibold text-foreground sm:text-4xl"
            >
              Three systems, one accountable settlement view.
            </h2>
          </ParallaxLayer>
          <ParallaxLayer layer="3">
            <ol className="mt-10 grid gap-3 lg:grid-cols-3">
              {PROBLEM_SOLUTION_STEPS.map((step, index) => (
                <ProblemSolutionStep key={step.eyebrow} step={step} index={index} report={report} />
              ))}
            </ol>
          </ParallaxLayer>
        </ParallaxScene>
      </SectionReveal>
    </section>
  );
}

const CONSOLE_SLIDES: CoverflowSlide[] = [
  {
    src: runsShot.url,
    alt: "Runs screen of the reconciliation console, listing every run with match rate and unresolved count",
    title: "Runs",
    subtitle: "Every reconciliation run, with its match rate and unresolved count side by side.",
    details: [
      "You are looking at the run index: one row per published run, newest first.",
      "It matters because the run you select here drives every other screen in the console.",
    ],
    zoom: 1.5,
    focus: "left top",
  },
  {
    src: dashboardShot.url,
    alt: "Run Dashboard screen showing headline metrics, link confusion matrices and vocabularies",
    title: "Run Dashboard",
    subtitle: "The at-a-glance summary of how one run actually went.",
    details: [
      "Headline metrics sit on top, with link confusion counts and resolved-tag vocabularies below.",
      "It matters because every rate shows its numerator and denominator, so nothing is a bare percentage.",
    ],
    zoom: 1.5,
    focus: "left top",
  },
  {
    src: exceptionsShot.url,
    alt: "Exceptions workqueue screen with filters and unresolved items awaiting triage",
    title: "Exceptions",
    subtitle: "The queue where unclear items wait for an operator decision.",
    details: [
      "Each row is one unresolved break with its bucket, amount delta and source links.",
      "It matters because closures are recorded with evidence and remain reversible.",
    ],
    zoom: 1.5,
    focus: "left top",
  },
  {
    src: agentTraceShot.url,
    alt: "Agent Trace screen listing each agent call in sequence with inputs and outputs",
    title: "Agent Trace",
    subtitle: "Exactly what the bounded agent reviewed, step by step.",
    details: [
      "Every agent call is listed in order with its inputs, tool use and returned verdict.",
      "It matters because an agent decision you cannot inspect is not auditable.",
    ],
    zoom: 1.5,
    focus: "left top",
  },
  {
    src: evalLabShot.url,
    alt: "Eval Lab screen comparing dev, holdout and regression seed sweeps",
    title: "Eval Lab",
    subtitle: "Tested against data the system has never seen, before it is trusted.",
    details: [
      "Dev, holdout and regression seed sweeps are kept apart, with ablation arms compared directly.",
      "It matters because the gate value is the worst holdout seed, not the best demo seed.",
    ],
    zoom: 1.5,
    focus: "left top",
  },
  {
    src: verifyShot.url,
    alt: "Verify screen showing computed checks, negative controls and falsifiers",
    title: "Verify",
    subtitle: "The proof surface: every check computed from fetched rows.",
    details: [
      "Anti-slop checks, negative controls and falsifiers each print the evidence behind their verdict.",
      "It matters because a control that cannot fail proves nothing.",
    ],
    zoom: 1.5,
    focus: "left top",
  },
];

function ConsoleShowcase() {
  return (
    <section className="border-b border-border bg-surface py-24" aria-labelledby="showcase-title">
      <SectionReveal
        dataProbe="showcase-section"
        className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"
      >
        <ParallaxScene probe="showcase-parallax">
          <ParallaxLayer layer="4" className="max-w-3xl">
            <div className="label-micro mb-3">Screenshot tour</div>
            <h2
              id="showcase-title"
              className="font-mono text-3xl font-semibold text-foreground sm:text-4xl"
            >
              See every part of the console.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground sm:text-base">
              Six operator screens, captured from the running app. Drag, use the arrows, or the left
              and right keys to move through them.
            </p>
          </ParallaxLayer>
          <ParallaxLayer layer="3">
            <CoverflowCarousel
              className="mt-10"
              label="Console screenshots"
              slides={CONSOLE_SLIDES}
              loop
              showCaption
              showNavigation
              showPagination
              cardWidth="clamp(280px, 46vw, 620px)"
              cardClassName="border border-border-strong bg-card"
            />
          </ParallaxLayer>
        </ParallaxScene>
      </SectionReveal>
    </section>
  );
}

function ProblemSolutionStep({
  step,
  index,
  report,
}: {
  step: (typeof PROBLEM_SOLUTION_STEPS)[number];
  index: number;
  report: ReconciliationReport | null;
}) {
  const reduced = usePrefersReducedMotion();
  const Icon = step.icon;
  const toneClass =
    step.accent === "risk"
      ? "border-[color:var(--landing-risk)] bg-[color:color-mix(in_oklab,var(--landing-risk)_10%,transparent)] text-[color:var(--landing-risk)]"
      : step.accent === "warning"
        ? "border-warning/55 bg-warning/10 text-warning"
        : "border-matched/55 bg-matched/10 text-matched";
  const resultDetail =
    step.accent === "primary" && report
      ? `${percent(report.accuracy.match_rate)} matched from ${provenance(report.accuracy.match_rate, "items")}; ${formatCount(unresolvedTotal(report.unresolved))} unresolved items remain visible.`
      : step.detail;

  return (
    <motion.li
      initial={reduced ? false : { opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px", amount: 0.2 }}
      transition={{
        duration: reduced ? 0 : 0.34,
        ease: MOTION_EASE,
        delay: reduced ? 0 : index * 0.05,
      }}
      className="rounded-md border border-border bg-card p-6"
    >
      <div className={cn("mb-7 grid size-12 place-items-center rounded border", toneClass)}>
        <Icon className="size-5" aria-hidden="true" />
      </div>
      <div className="label-micro">
        Step {index + 1} · {step.eyebrow}
      </div>
      <h3 className="mt-3 font-mono text-2xl font-semibold leading-tight text-foreground">
        {step.title}
      </h3>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{resultDetail}</p>
    </motion.li>
  );
}

function FeatureGrid({ report }: { report: ReconciliationReport | null }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <section
      className="relative border-b border-border bg-surface/30 py-24"
      aria-labelledby="features-title"
    >
      <div className="absolute inset-x-0 top-0 h-px bg-border-strong" aria-hidden="true" />
      <SectionReveal dataProbe="feature-section" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ParallaxScene probe="feature-parallax">
          <ParallaxLayer layer="4" className="max-w-3xl">
            <div className="label-micro mb-3">Implemented surfaces</div>
            <h2
              id="features-title"
              className="font-mono text-3xl font-semibold text-foreground sm:text-4xl"
            >
              Built for finance operators who need evidence, not vibes.
            </h2>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              Every capability below exists in the app: run dashboards, exception triage, trace
              review, evaluation lab and verification pages all read the same live reconciliation
              record.
            </p>
          </ParallaxLayer>
          <ParallaxLayer layer="3">
            <div className="mt-10 grid gap-3 lg:grid-cols-4 lg:items-start">
              {FEATURES.map((feature) => (
                <FeatureCard
                  key={feature.title}
                  feature={feature}
                  report={report}
                  expanded={expanded === feature.title}
                  onToggle={() => setExpanded(expanded === feature.title ? null : feature.title)}
                />
              ))}
              <CtaFeatureCard />
            </div>
          </ParallaxLayer>
        </ParallaxScene>
      </SectionReveal>
    </section>
  );
}

function FeatureCard({
  feature,
  report,
  expanded,
  onToggle,
}: {
  feature: (typeof FEATURES)[number];
  report: ReconciliationReport | null;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { title, body, icon: Icon, size, visual, accent } = feature;
  const reduced = usePrefersReducedMotion();
  const { controls, pulsing, trigger } = usePressPulse(reduced);
  const accentClasses = featureAccentClasses(accent);

  return (
    <motion.article
      role="button"
      data-feature-card="true"
      data-pressed={pulsing ? "true" : undefined}
      animate={controls}
      tabIndex={0}
      aria-pressed={expanded}
      onPointerDown={trigger}
      onClick={onToggle}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          trigger();
          onToggle();
        }
      }}
      className={cn(
        "group relative cursor-pointer origin-center overflow-hidden rounded-md border bg-card p-5 text-left transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
        accentClasses.card,
        expanded && accentClasses.expanded,
        size,
      )}
    >
      <div className="relative">
        <div className="mb-5 flex items-center justify-between gap-3">
          <span
            className={cn(
              "grid size-10 place-items-center rounded border bg-muted",
              accentClasses.icon,
            )}
          >
            <Icon className="size-5" aria-hidden="true" />
          </span>
          <span className="label-micro">live module</span>
        </div>
        <h3 className="font-mono text-base font-semibold text-foreground">{title}</h3>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{body}</p>
        {expanded ? (
          <div className={cn("mt-4 rounded border px-3 py-2", accentClasses.selected)}>
            <div className="label-micro">selected module</div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Pressed state locks this tile for review; linked product surfaces below open the live
              module.
            </p>
          </div>
        ) : null}
        <FeatureVisual visual={visual} report={report} accent={accent} />
      </div>
    </motion.article>
  );
}

function featureAccentClasses(accent: FeatureAccent): {
  card: string;
  icon: string;
  expanded: string;
  selected: string;
  text: string;
  subtle: string;
  border: string;
} {
  if (accent === "warning") {
    return {
      card: "border-border border-l-2 border-l-warning/55 hover:border-warning/45",
      icon: "border-warning/45 bg-warning/10 text-warning",
      expanded: "border-warning/65 bg-background",
      selected: "border-warning/35 bg-warning/10",
      text: "text-warning",
      subtle: "bg-warning/10",
      border: "border-warning/45",
    };
  }
  if (accent === "violet") {
    return {
      card: "border-border border-l-2 border-l-[color:var(--landing-violet)] hover:border-[color:var(--landing-violet)]",
      icon: "border-[color:color-mix(in_oklab,var(--landing-violet)_45%,transparent)] bg-[color:color-mix(in_oklab,var(--landing-violet)_10%,transparent)] text-[color:var(--landing-violet)]",
      expanded:
        "border-[color:color-mix(in_oklab,var(--landing-violet)_65%,transparent)] bg-background",
      selected:
        "border-[color:color-mix(in_oklab,var(--landing-violet)_35%,transparent)] bg-[color:color-mix(in_oklab,var(--landing-violet)_10%,transparent)]",
      text: "text-[color:var(--landing-violet)]",
      subtle: "bg-[color:color-mix(in_oklab,var(--landing-violet)_10%,transparent)]",
      border: "border-[color:color-mix(in_oklab,var(--landing-violet)_45%,transparent)]",
    };
  }
  if (accent === "sky") {
    return {
      card: "border-border border-l-2 border-l-info/55 hover:border-info/45",
      icon: "border-info/45 bg-info/10 text-info",
      expanded: "border-info/65 bg-background",
      selected: "border-info/35 bg-info/10",
      text: "text-info",
      subtle: "bg-info/10",
      border: "border-info/45",
    };
  }
  return {
    card: "border-border border-l-2 border-l-primary/55 hover:border-primary/45",
    icon: "border-primary/45 bg-primary/10 text-primary",
    expanded: "border-primary/65 bg-background",
    selected: "border-primary/35 bg-primary/10",
    text: "text-primary",
    subtle: "bg-primary/10",
    border: "border-primary/45",
  };
}

function CtaFeatureCard() {
  const reduced = usePrefersReducedMotion();
  const { controls, pulsing, trigger } = usePressPulse(reduced);

  return (
    <motion.article
      data-feature-card="true"
      data-pressed={pulsing ? "true" : undefined}
      animate={controls}
      onPointerDown={trigger}
      className="group relative flex origin-center flex-col justify-between overflow-hidden rounded-md border border-primary/40 bg-primary/5 p-5 transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-primary/70 lg:col-span-2"
    >
      <div className="relative">
        <div className="mb-5 flex items-center justify-between gap-3">
          <span className="grid size-10 place-items-center rounded border border-primary/40 bg-primary/10 text-primary">
            <ShieldCheck className="size-5" aria-hidden="true" />
          </span>
          <span className="label-micro">exit point</span>
        </div>
        <h3 className="font-mono text-base font-semibold text-foreground">Review verification</h3>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          See the anti-slop checks, negative controls and falsifiers the engine must pass before any
          confidence is claimed.
        </p>
      </div>
      <TapTarget glow className="mt-6 w-full">
        <Button asChild variant="outline" className="w-full justify-between">
          <Link to="/verify">
            Open Verify
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      </TapTarget>
    </motion.article>
  );
}

function FeatureVisual({
  visual,
  report,
  accent,
}: {
  visual: string;
  report: ReconciliationReport | null;
  accent: FeatureAccent;
}) {
  const accentClasses = featureAccentClasses(accent);
  if (visual === "match" && report) {
    const width = `${Math.max(0, Math.min(100, report.accuracy.match_rate.value * 100))}%`;
    return (
      <div className="mt-8 rounded-md border border-border bg-background/60 p-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <div className="label-micro">latest match rate</div>
            <div className={cn("tnum mt-2 text-3xl font-semibold", accentClasses.text)}>
              {percent(report.accuracy.match_rate)}
            </div>
          </div>
          <div className="tnum text-right text-xs text-muted-foreground">
            {provenance(report.accuracy.match_rate, "items")}
          </div>
        </div>
        <svg
          viewBox="0 0 100 8"
          role="img"
          aria-label="Latest match rate bar"
          className="mt-4 h-2 w-full overflow-hidden rounded bg-muted"
        >
          <rect
            width={width}
            height="8"
            rx="4"
            className={cn("fill-current", accentClasses.text)}
          />
        </svg>
        <dl className="mt-4 grid gap-2 border-t border-border pt-3 sm:grid-cols-3">
          <div>
            <dt className="label-micro">unresolved items</dt>
            <dd className="tnum mt-1 text-sm text-unresolved">
              {formatCount(unresolvedTotal(report.unresolved))}
            </dd>
          </div>
          <div>
            <dt className="label-micro">seed / set</dt>
            <dd className="tnum mt-1 text-sm text-foreground">
              {formatCount(report.config.seed)} · {report.config.seed_set}
            </dd>
          </div>
          <div>
            <dt className="label-micro">engine</dt>
            <dd className="tnum mt-1 truncate text-sm text-foreground">{report.engine_version}</dd>
          </div>
        </dl>
      </div>
    );
  }

  if (visual === "verify") {
    return (
      <div className="mt-8 grid gap-2">
        {["rates reconcile", "no truth leak", "cost honesty"].map((label) => (
          <div
            key={label}
            className={cn(
              "flex items-center justify-between rounded border bg-background/60 px-3 py-2",
              accentClasses.border,
            )}
          >
            <span className="text-xs text-muted-foreground">{label}</span>
            <span className="label-micro rounded border border-matched/50 px-1.5 py-0.5 text-matched">
              checked
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (visual === "trace") {
    return (
      <div
        className={cn(
          "mt-8 space-y-2 rounded-md border bg-background/60 p-3",
          accentClasses.border,
        )}
      >
        {[
          ["prompt", "redacted"],
          ["tools", "bounded"],
          ["guardrail", "reasons shown"],
        ].map(([label, value]) => (
          <div key={label} className="grid grid-cols-[5rem_1fr] gap-3 text-xs">
            <span className="label-micro">{label}</span>
            <span className="tnum truncate text-muted-foreground">{value}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "mt-8 flex items-center gap-3 rounded-md border bg-background/60 p-3",
        accentClasses.border,
      )}
    >
      <RadioTower className={cn("size-4", accentClasses.text)} aria-hidden="true" />
      <div className="min-w-0">
        <div className="text-xs font-medium text-foreground">request status streams back live</div>
        <div className="tnum mt-1 text-xs text-muted-foreground">
          no fixture layer in the cockpit
        </div>
      </div>
    </div>
  );
}

const FLOW: Array<{ title: string; detail: string; icon: LucideIcon; icons?: LucideIcon[] }> = [
  {
    title: "Source systems feed in",
    detail: "Bank statements, gateway payouts and ledger entries remain visibly separate.",
    icon: Banknote,
    icons: [Banknote, Braces, FileSearch],
  },
  {
    title: "Rules plus bounded agent reconcile",
    detail: "Deterministic matches lead; agent review is constrained to residuals and evidence.",
    icon: GitBranch,
  },
  {
    title: "Evidence lands in Verify",
    detail: "Exceptions, closures and controls are checked before confidence is claimed.",
    icon: ShieldCheck,
  },
];

function HowItWorks() {
  const reduced = usePrefersReducedMotion();

  return (
    <section className="relative py-24" aria-labelledby="flow-title">
      <SectionReveal dataProbe="flow-section" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ParallaxScene probe="flow-parallax">
          <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-start">
            <ParallaxLayer layer="4">
              <div className="label-micro mb-3">Operating model</div>
              <h2
                id="flow-title"
                className="font-mono text-3xl font-semibold text-foreground sm:text-4xl"
              >
                From settlement records to falsifiable closure.
              </h2>
              <p className="mt-4 text-base leading-7 text-muted-foreground">
                The workflow keeps source systems, matching logic, exception handling and
                verification visibly separated so a reviewer can trace every claim back to fetched
                evidence.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                <TapTarget>
                  <Button asChild variant="outline">
                    <Link to="/dashboard">Open dashboard</Link>
                  </Button>
                </TapTarget>
                <TapTarget>
                  <Button asChild variant="ghost">
                    <Link to="/agent-trace">Inspect trace</Link>
                  </Button>
                </TapTarget>
              </div>
            </ParallaxLayer>
            <ParallaxLayer layer="3">
              <ol className="grid gap-3 lg:grid-cols-3">
                {FLOW.map(({ title, detail, icon: Icon, icons }, index) => (
                  <motion.li
                    key={title}
                    {...(reduced ? {} : { whileTap: { scale: 0.97 } })}
                    transition={{ duration: reduced ? 0 : 0.12, ease: MOTION_EASE }}
                    className="relative rounded-md border border-border bg-card p-5 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:border-primary/40 active:scale-[0.97] motion-reduce:active:scale-100"
                  >
                    {index < FLOW.length - 1 ? (
                      <ChevronRight
                        className="absolute -right-3 top-1/2 z-10 hidden size-6 -translate-y-1/2 rounded-full border border-border bg-background p-1 text-primary lg:block"
                        aria-hidden="true"
                      />
                    ) : null}
                    <div className="mb-8 flex items-center gap-2">
                      {icons ? (
                        icons.map((SmallIcon) => (
                          <span
                            key={SmallIcon.displayName ?? SmallIcon.name}
                            className="grid size-9 place-items-center rounded border border-border bg-surface text-primary"
                          >
                            <SmallIcon className="size-4" aria-hidden="true" />
                          </span>
                        ))
                      ) : (
                        <span className="grid size-10 place-items-center rounded border border-border bg-surface text-primary">
                          <Icon className="size-5" aria-hidden="true" />
                        </span>
                      )}
                    </div>
                    <h3 className="font-mono text-base font-semibold text-foreground">{title}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{detail}</p>
                  </motion.li>
                ))}
              </ol>
            </ParallaxLayer>
          </div>
        </ParallaxScene>
      </SectionReveal>
    </section>
  );
}

const SETUP_STEPS: Array<{
  title: string;
  detail: string;
  commands: string[];
}> = [
  {
    title: "Generate dataset",
    detail: "Create the deterministic settlement input rows consumed by the recon engine.",
    commands: ["uv run python -m engine.cli generate --n 100 --seed 42 --out data"],
  },
  {
    title: "Run reconciliation",
    detail: "Publish a rules-plus-agent run report that the dashboard can read.",
    commands: [
      "uv run python -m engine.cli run --mode rules_agent --seeds 42 --n 100 --report-out reports/run_42.json --publish",
    ],
  },
  {
    title: "Evaluate",
    detail: "Run the holdout sweep and ablation arms used by the evaluation lab.",
    commands: [
      "uv run python -m engine.eval.sweep --seeds 101-120",
      "uv run python -m engine.eval.ablation --seeds 101-120",
    ],
  },
  {
    title: "Verify",
    detail: "Crosscheck the selected run, then execute the negative controls.",
    commands: [
      "uv run python -m engine.tools.crosscheck --run <run_id>",
      "uv run python -m engine.tools.crosscheck --run <run_id> --controls",
    ],
  },
  {
    title: "Launch dashboard",
    detail: "Start the UI against the published run data.",
    commands: ["cd ui && bun install && bun run dev"],
  },
];

function GettingStarted() {
  return (
    <section className="border-y border-border bg-background py-24" aria-labelledby="setup-title">
      <SectionReveal dataProbe="setup-section" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-start">
          <div>
            <div className="label-micro mb-3">Getting started</div>
            <h2
              id="setup-title"
              className="font-mono text-3xl font-semibold text-foreground sm:text-4xl"
            >
              Reproduce the recon pipeline before opening the console.
            </h2>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              Generate data, publish a run, evaluate holdouts, crosscheck controls and launch the
              dashboard from the same terminal sequence.
            </p>
            <p className="mt-5 text-sm text-muted-foreground">
              Full guide:{" "}
              <a
                href="README.md"
                className="font-mono text-primary underline-offset-4 hover:underline"
              >
                README.md
              </a>{" "}
              /{" "}
              <a
                href="VERIFICATION.md"
                className="font-mono text-primary underline-offset-4 hover:underline"
              >
                VERIFICATION.md
              </a>
            </p>
          </div>
          <ol className="grid gap-3">
            {SETUP_STEPS.map((step, index) => (
              <li
                key={step.title}
                className="grid gap-3 rounded-md border border-border bg-card p-4 sm:grid-cols-[7rem_1fr]"
              >
                <div>
                  <div className="label-micro">step {index + 1}</div>
                  <div className="mt-2 font-mono text-sm font-semibold text-foreground">
                    {step.title}
                  </div>
                </div>
                <div className="min-w-0">
                  <p className="text-sm leading-6 text-muted-foreground">{step.detail}</p>
                  <div className="mt-3 grid gap-2">
                    {step.commands.map((command) => (
                      <CopyCommand key={command} command={command} />
                    ))}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </SectionReveal>
    </section>
  );
}

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  async function copyCommand() {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(command);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 900);
  }

  return (
    <div className="grid gap-2 rounded border border-border bg-background/70 p-3 sm:grid-cols-[1fr_auto] sm:items-center">
      <pre className="min-w-0 overflow-x-auto whitespace-pre py-1">
        <code className="tnum text-xs leading-5 text-foreground">{command}</code>
      </pre>
      <TapTarget className="justify-self-start sm:justify-self-end">
        <Button type="button" variant="ghost" size="sm" className="font-mono" onClick={copyCommand}>
          <Clipboard aria-hidden="true" />
          {copied ? "Copied" : "Copy"}
        </Button>
      </TapTarget>
    </div>
  );
}

function ProductPreview() {
  return (
    <section
      id="proof"
      className="border-y border-border bg-surface/35 py-24"
      aria-labelledby="proof-title"
    >
      <SectionReveal dataProbe="proof-section" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ParallaxScene
          className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-center"
          probe="proof-parallax"
        >
          <ParallaxLayer layer="4" className="max-w-xl">
            <div className="label-micro mb-3">Proof surface</div>
            <h2
              id="proof-title"
              className="font-mono text-3xl font-semibold text-foreground sm:text-4xl"
            >
              The product shows its work before it asks for trust.
            </h2>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              Verify renders computed anti-slop checks, negative controls and falsifiers from the
              selected run. The frame is a real screenshot of the app, not a fabricated marketing
              mock.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <TapTarget>
                <Button asChild variant="outline">
                  <Link to="/verify">Open Verify</Link>
                </Button>
              </TapTarget>
              <TapTarget>
                <Button asChild variant="ghost">
                  <Link to="/agent-trace">Inspect trace</Link>
                </Button>
              </TapTarget>
            </div>
          </ParallaxLayer>
          <ParallaxLayer layer="2">
            <BrowserFrame
              image={verifyPreview}
              alt="Real Verify page showing anti-slop checks and evidence rows"
              title="Verify · computed evidence checks"
              href="/verify"
              className="shadow-[0_30px_90px_color-mix(in_oklab,var(--background)_72%,transparent)]"
            />
          </ParallaxLayer>
        </ParallaxScene>
      </SectionReveal>
    </section>
  );
}

function LandingFooter() {
  const groups = [
    {
      label: "Product",
      links: [
        ["Runs", "/runs"],
        ["Dashboard", "/dashboard"],
        ["Verify", "/verify"],
      ],
    },
    {
      label: "Resources",
      links: [
        ["Method", "#proof"],
        ["Controls", "/eval-lab"],
        ["Trace", "/agent-trace"],
      ],
    },
    {
      label: "Legal",
      links: [
        ["Security", "#"],
        ["Privacy", "#"],
        ["Terms", "#"],
      ],
    },
  ];

  return (
    <footer className="border-t border-border bg-background py-12">
      <SectionReveal
        dataProbe="footer-section"
        className="mx-auto grid max-w-7xl gap-10 px-4 text-sm text-muted-foreground sm:px-6 lg:grid-cols-[1.2fr_1fr] lg:px-8"
      >
        <div className="max-w-md">
          <Link
            to="/"
            className="inline-flex items-center gap-3"
            aria-label="Settlement Sentinel home"
          >
            <span className="flex shrink-0 items-center rounded border border-primary/50 bg-foreground px-1.5 py-1">
              <img src={razorpayLogo} alt="Razorpay" className="h-5 w-auto" />
            </span>

            <span>
              <span className="block font-mono font-semibold text-foreground">
                Settlement Sentinel / RECON
              </span>
              <span className="label-micro block">3-way settlement</span>
            </span>
          </Link>
          <p className="mt-4 leading-6">
            Built for deterministic, audit-grade settlement reconciliation where every rate has a
            numerator, denominator and trail.
          </p>
        </div>
        <nav className="grid gap-8 sm:grid-cols-3" aria-label="Footer">
          {groups.map((group) => (
            <div key={group.label}>
              <div className="label-micro mb-3">{group.label}</div>
              <ul className="space-y-2">
                {group.links.map(([label, href]) => (
                  <li key={label}>
                    <a href={href} className="hover:text-foreground">
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </SectionReveal>
    </footer>
  );
}
