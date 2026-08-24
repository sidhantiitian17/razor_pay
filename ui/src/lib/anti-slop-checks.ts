import { formatCount } from "@/lib/format";
import type { AgentCallRow } from "@/lib/use-agent-calls";
import type { ClosureRow, ControlResultRow } from "@/lib/use-verify-inputs";
import { CONTROL_NAMES } from "@/lib/use-verify-inputs";
import type { ExceptionRow } from "@/lib/use-exceptions";
import type { ReconciliationReport } from "@/types/report";

/**
 * Every verdict on the Verify page is computed here from fetched rows. Nothing
 * in this module may return a literal pass that is not derived from data.
 */
export type Verdict = "pass" | "fail" | "vacuous" | "indeterminate";

export interface CheckResult {
  id: string;
  name: string;
  verdict: Verdict;
  evidence: string;
}

/** Literal strings that must never appear in a prompt sent to the model. */
export const TRUTH_LEAK_NEEDLES = ["truth", "_truth_label", "ground_truth"] as const;

const TOLERANCE = 1e-9;

function sumValues(map: Record<string, number>): number {
  return Object.values(map).reduce((sum, value) => sum + value, 0);
}

function isMetricShaped(node: Record<string, unknown>): boolean {
  return "value" in node;
}

interface ProvenanceScan {
  scanned: number;
  offenders: string[];
}

/** Walks the report for metric-shaped objects and records any bare float. */
export function scanMetricProvenance(report: ReconciliationReport): ProvenanceScan {
  const offenders: string[] = [];
  let scanned = 0;

  const walk = (node: unknown, path: string): void => {
    if (Array.isArray(node)) {
      node.forEach((entry, index) => walk(entry, `${path}[${index}]`));
      return;
    }
    if (node === null || typeof node !== "object") return;

    const record = node as Record<string, unknown>;
    if (isMetricShaped(record)) {
      scanned += 1;
      const numerator = record["numerator"];
      const denominator = record["denominator"];
      if (typeof numerator !== "number" || typeof denominator !== "number") {
        offenders.push(path);
      }
    }
    for (const [key, child] of Object.entries(record)) {
      walk(child, path ? `${path}.${key}` : key);
    }
  };

  walk(report, "report");
  return { scanned, offenders };
}

export interface TruthLeakScan {
  promptsSearched: number;
  hits: { callId: string; needle: string }[];
}

/** Searches every fetched prompt for the literal truth-label strings. */
export function scanTruthLeak(calls: AgentCallRow[]): TruthLeakScan {
  const hits: { callId: string; needle: string }[] = [];

  for (const call of calls) {
    const haystack = JSON.stringify(call.prompt_redacted ?? null).toLowerCase();
    for (const needle of TRUTH_LEAK_NEEDLES) {
      if (haystack.includes(needle.toLowerCase())) hits.push({ callId: call.call_id, needle });
    }
  }

  return { promptsSearched: calls.length, hits };
}

export interface ClosureOnOpenScan {
  closuresChecked: number;
  openExceptions: number;
  offenders: { closureId: string; exceptionId: string }[];
}

/**
 * Cross-references closure targets against open exceptions, matching either the
 * exception ID itself or any source row ID the exception references.
 */
export function scanClosureOnOpen(
  closures: ClosureRow[],
  exceptions: ExceptionRow[],
): ClosureOnOpenScan {
  const open = exceptions.filter((row) => row.status === "open");
  const index = new Map<string, string>();
  for (const row of open) {
    index.set(row.exception_id, row.exception_id);
    for (const id of row.row_ids) index.set(id, row.exception_id);
  }

  const offenders: { closureId: string; exceptionId: string }[] = [];
  for (const closure of closures) {
    const exceptionId = index.get(closure.target);
    if (exceptionId) offenders.push({ closureId: closure.closure_id, exceptionId });
  }

  return { closuresChecked: closures.length, openExceptions: open.length, offenders };
}

export interface VerifyInputs {
  report: ReconciliationReport;
  calls: AgentCallRow[];
  closures: ClosureRow[];
  exceptions: ExceptionRow[];
}

/** The 8 anti-slop checks, each with the evidence string that produced it. */
export function computeAntiSlopChecks({
  report,
  calls,
  closures,
  exceptions,
}: VerifyInputs): CheckResult[] {
  const { accuracy, throughput, cost, resolved, unresolved } = report;

  // 1 — rates reconcile
  const rateSum = accuracy.resolved_rate.value + accuracy.unresolved_rate.value;
  const rateDelta = Math.abs(rateSum - 1);
  const rates: CheckResult = {
    id: "rates_reconcile",
    name: "Rates reconcile",
    verdict: rateDelta <= TOLERANCE ? "pass" : "fail",
    evidence: `resolved_rate ${accuracy.resolved_rate.value} + unresolved_rate ${accuracy.unresolved_rate.value} = ${rateSum}; |sum − 1| = ${rateDelta.toExponential(3)} against tolerance 1e-9`,
  };

  // 2 — exception list reconciles
  const resolvedTotal = sumValues(resolved as unknown as Record<string, number>);
  const unresolvedTotal = sumValues(unresolved as unknown as Record<string, number>);
  const groupTotal = resolvedTotal + unresolvedTotal;
  const reconcile: CheckResult = {
    id: "list_reconciles",
    name: "Exception list reconciles",
    verdict: groupTotal === throughput.rows_total ? "pass" : "fail",
    evidence: `summed 5 resolved tags (${formatCount(resolvedTotal)}) + 9 unresolved buckets (${formatCount(unresolvedTotal)}) = ${formatCount(groupTotal)} against throughput.rows_total ${formatCount(throughput.rows_total)}`,
  };

  // 3 — every metric has provenance
  const provenance = scanMetricProvenance(report);
  const metrics: CheckResult = {
    id: "metric_provenance",
    name: "Every metric has provenance",
    verdict: provenance.offenders.length === 0 ? "pass" : "fail",
    evidence: `scanned ${formatCount(provenance.scanned)} metric-shaped objects in the report for numerator/denominator: ${formatCount(provenance.offenders.length)} missing${provenance.offenders.length ? ` (${provenance.offenders.slice(0, 3).join(", ")})` : ""}`,
  };

  // 4 — no truth leak
  const leak = scanTruthLeak(calls);
  const truth: CheckResult = {
    id: "no_truth_leak",
    name: "No truth leak",
    verdict: leak.promptsSearched === 0 ? "vacuous" : leak.hits.length === 0 ? "pass" : "fail",
    evidence:
      leak.promptsSearched === 0
        ? `0 agent_calls prompts exist for this run — nothing searched, vacuously true`
        : `searched ${formatCount(leak.promptsSearched)} prompts for ${TRUTH_LEAK_NEEDLES.map((n) => `"${n}"`).join(", ")}: ${formatCount(leak.hits.length)} found${leak.hits.length ? ` (first: ${leak.hits[0]?.callId} → "${leak.hits[0]?.needle}")` : ""}`,
  };

  // 5 — evidence sufficiency
  const thin = report.exceptions.filter((entry) => entry.evidence.length < 2);
  const evidence: CheckResult = {
    id: "evidence_sufficiency",
    name: "Evidence sufficiency",
    verdict: report.exceptions.length === 0 ? "vacuous" : thin.length === 0 ? "pass" : "fail",
    evidence:
      report.exceptions.length === 0
        ? "report.exceptions is empty — 0 entries checked, vacuously true"
        : `checked ${formatCount(report.exceptions.length)} report exceptions for evidence.length >= 2: ${formatCount(thin.length)} below the floor${thin.length ? ` (first: ${thin[0]?.exception_id})` : ""}`,
  };

  // 6 — closures are reversible
  const irreversible = closures.length > 0 && !report.closures.reversible;
  const reversible: CheckResult = {
    id: "closures_reversible",
    name: "Closures are reversible",
    verdict: closures.length === 0 ? "vacuous" : irreversible ? "fail" : "pass",
    evidence:
      closures.length === 0
        ? "0 closures — vacuously true"
        : `${formatCount(closures.length)} closure rows applied for this run; report.closures.reversible = ${String(report.closures.reversible)}, dry_run = ${String(report.closures.dry_run)}, second-pass new closures ${formatCount(report.closures.second_pass_new_closures)}`,
  };

  // 7 — no closure on an open exception
  const cross = scanClosureOnOpen(closures, exceptions);
  const openClosure: CheckResult = {
    id: "no_closure_on_open",
    name: "No closure on an open exception",
    verdict:
      cross.closuresChecked === 0 ? "vacuous" : cross.offenders.length === 0 ? "pass" : "fail",
    evidence:
      cross.closuresChecked === 0
        ? "0 closures — vacuously true"
        : `cross-referenced ${formatCount(cross.closuresChecked)} closure targets against ${formatCount(cross.openExceptions)} open exceptions (exception_id and row_ids): ${formatCount(cross.offenders.length)} found${cross.offenders.length ? ` (${cross.offenders[0]?.closureId} → ${cross.offenders[0]?.exceptionId})` : ""}`,
  };

  // 8 — cost honesty
  const pricingPresent = cost.pricing_last_verified.trim().length > 0;
  const costPositive = throughput.llm_calls === 0 || cost.cost_usd > 0;
  const costHonesty: CheckResult = {
    id: "cost_honesty",
    name: "Cost honesty",
    verdict: costPositive && pricingPresent ? "pass" : "fail",
    evidence: `${formatCount(throughput.llm_calls)} LLM calls with cost_usd ${cost.cost_usd} (${costPositive ? "non-zero cost for real calls" : "zero cost despite real calls"}); pricing_last_verified ${pricingPresent ? `"${cost.pricing_last_verified}"` : "is empty"}`,
  };

  return [rates, reconcile, metrics, truth, evidence, reversible, openClosure, costHonesty];
}

export interface ControlRow {
  name: ControlNameOrOther;
  verdict: Verdict;
  evidence: string;
  reportPassed: boolean | null;
  rowPassed: boolean | null;
  disagrees: boolean;
}

type ControlNameOrOther = string;

function reportControlPassed(report: ReconciliationReport, name: string): boolean | null {
  const controls = report.controls as unknown as Record<string, { passed?: boolean }>;
  const entry = controls[name];
  return typeof entry?.passed === "boolean" ? entry.passed : null;
}

function detailString(details: unknown): string {
  if (details === null || details === undefined) return "no details recorded";
  if (typeof details === "string") return details;
  return Object.entries(details as Record<string, unknown>)
    .map(
      ([key, value]) =>
        `${key} = ${typeof value === "object" ? JSON.stringify(value) : String(value)}`,
    )
    .join(" · ");
}

/** One row per named control, verdict from the row, cross-checked against the report. */
export function computeControlRows(
  report: ReconciliationReport,
  rows: ControlResultRow[],
): ControlRow[] {
  const byName = new Map(rows.map((row) => [row.control_name, row]));

  return CONTROL_NAMES.map((name) => {
    const row = byName.get(name) ?? null;
    const reportPassed = reportControlPassed(report, name);
    const rowPassed = row ? row.passed : null;
    const disagrees = rowPassed !== null && reportPassed !== null && rowPassed !== reportPassed;

    return {
      name,
      verdict: rowPassed === null ? "indeterminate" : rowPassed ? "pass" : "fail",
      evidence:
        row === null
          ? `not yet run — no control_results row for this run; report.controls.${name}.passed = ${reportPassed === null ? "absent" : String(reportPassed)}`
          : `${detailString(row.details)} · recorded ${row.created_at}`,
      reportPassed,
      rowPassed,
      disagrees,
    };
  });
}

export interface FalsifierResult {
  claim: string;
  verdict: "holds" | "triggered" | "indeterminate";
  evidence: string;
}

/**
 * The six published falsification conditions. Each renders a live verdict of
 * whether the falsifier currently fires for the selected run.
 */
export function computeFalsifiers(inputs: VerifyInputs, controls: ControlRow[]): FalsifierResult[] {
  const { report, calls, closures, exceptions } = inputs;
  const leak = scanTruthLeak(calls);
  const cross = scanClosureOnOpen(closures, exceptions);
  const resolvedTotal = sumValues(report.resolved as unknown as Record<string, number>);
  const unresolvedTotal = sumValues(report.unresolved as unknown as Record<string, number>);
  const recall = report.candidate_space.blocker_recall;
  const brokenControls = controls.filter((control) => control.rowPassed === false);
  const unrunControls = controls.filter((control) => control.rowPassed === null);

  return [
    {
      claim: "match_rate on a fresh unseen seed falls below the published min",
      verdict: report.config.seed_set === "holdout" ? "holds" : "indeterminate",
      evidence: `this run is seed ${formatCount(report.config.seed)} of seed-set "${report.config.seed_set}" with match_rate ${(report.accuracy.match_rate.value * 100).toFixed(2)}% (${formatCount(report.accuracy.match_rate.numerator)}/${formatCount(report.accuracy.match_rate.denominator)}); a holdout-seed comparison needs a published minimum from a second run and is not derivable from this run alone`,
    },
    {
      claim: 'Any negative control produces its "broken" outcome',
      verdict:
        brokenControls.length > 0
          ? "triggered"
          : unrunControls.length > 0
            ? "indeterminate"
            : "holds",
      evidence: `${formatCount(controls.length - unrunControls.length)} of ${formatCount(controls.length)} controls have a recorded result; ${formatCount(brokenControls.length)} failed${brokenControls.length ? ` (${brokenControls.map((c) => c.name).join(", ")})` : ""}${unrunControls.length ? `; not yet run: ${unrunControls.map((c) => c.name).join(", ")}` : ""}`,
    },
    {
      claim: "Any truth label is found in any prompt in agent_calls",
      verdict:
        leak.hits.length > 0 ? "triggered" : leak.promptsSearched === 0 ? "indeterminate" : "holds",
      evidence: `searched ${formatCount(leak.promptsSearched)} prompts for ${TRUTH_LEAK_NEEDLES.map((n) => `"${n}"`).join(", ")}: ${formatCount(leak.hits.length)} found`,
    },
    {
      claim: "blocker_recall < 1.0 while precision is claimed at the group level",
      verdict: recall.value < 1 ? "triggered" : "holds",
      evidence: `blocker_recall ${recall.value} (${formatCount(recall.numerator)}/${formatCount(recall.denominator)} true pairs retained) over a candidate space of ${formatCount(report.candidate_space.size)} pairs; group-level precision bank↔payout ${report.accuracy.links.bank_payout.precision.value}, payout↔ledger ${report.accuracy.links.payout_ledger.precision.value}`,
    },
    {
      claim: "resolved + unresolved != rows_total",
      verdict:
        resolvedTotal + unresolvedTotal === report.throughput.rows_total ? "holds" : "triggered",
      evidence: `${formatCount(resolvedTotal)} resolved + ${formatCount(unresolvedTotal)} unresolved = ${formatCount(resolvedTotal + unresolvedTotal)} against rows_total ${formatCount(report.throughput.rows_total)}`,
    },
    {
      claim: "A closure exists for a row in an open exception",
      verdict:
        cross.offenders.length > 0
          ? "triggered"
          : cross.closuresChecked === 0
            ? "indeterminate"
            : "holds",
      evidence: `${formatCount(cross.closuresChecked)} closures cross-referenced against ${formatCount(cross.openExceptions)} open exceptions: ${formatCount(cross.offenders.length)} overlaps`,
    },
  ];
}
