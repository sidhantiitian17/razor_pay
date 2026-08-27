"""Report and dataset publisher to storage port (§5.2, §7 P6, checks 6.1, 6.2, 6.3, 6.7, 6.8)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from engine.adapters.store_memory import MemoryStorageAdapter

if TYPE_CHECKING:
    from engine.core.generator.build import GeneratedDataset
    from engine.ports.store import StoragePort

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+"),
    re.compile(r"x-api-key", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
]


def _sanitize_secrets(obj: Any) -> Any:
    """Recursively scrub any sensitive authentication strings or tokens."""
    if isinstance(obj, str):
        cleaned = obj
        for pat in SECRET_PATTERNS:
            cleaned = pat.sub("[REDACTED]", cleaned)
        return cleaned
    if isinstance(obj, dict):
        return {
            k: _sanitize_secrets(v)
            for k, v in obj.items()
            if k.lower() not in ("authorization", "x-api-key")
        }
    if isinstance(obj, list):
        return [_sanitize_secrets(item) for item in obj]
    return obj


def _serialize_match_group(mg: Any) -> dict[str, Any]:
    if isinstance(mg, dict):
        return mg
    return {
        "group_id": getattr(mg, "group_id", ""),
        "kind": mg.kind.value if hasattr(mg.kind, "value") else str(mg.kind),
        "bank_ids": list(getattr(mg, "bank_ids", [])),
        "payout_ids": list(getattr(mg, "payout_ids", [])),
        "ledger_ids": list(getattr(mg, "ledger_ids", [])),
        "confidence": float(getattr(mg, "confidence", 1.0)),
        "source": str(getattr(mg, "source", "deterministic")),
        "fields_matched": list(getattr(mg, "fields_matched", [])),
        "tolerances_used": list(getattr(mg, "tolerances_used", [])),
        "tag": mg.tag.value if hasattr(mg.tag, "value") else str(getattr(mg, "tag", "")),
        "reason": str(getattr(mg, "reason", "")),
        "agent_turns": int(getattr(mg, "agent_turns", 0)),
    }


def _serialize_link_decision(ld: Any) -> dict[str, Any]:
    if isinstance(ld, dict):
        return ld
    return {
        "link_type": str(getattr(ld, "link_type", "")),
        "left_id": str(getattr(ld, "left_id", "")),
        "right_id": str(getattr(ld, "right_id", "")),
        "predicted": bool(getattr(ld, "predicted", False)),
        "truth": bool(getattr(ld, "truth", False)),
        "outcome": str(getattr(ld, "outcome", "")),
    }


def _serialize_agent_call_record(call: Any, run_id: str) -> dict[str, Any]:
    if isinstance(call, dict):
        rec = dict(call)
        rec["run_id"] = run_id
        return rec
    return {
        "call_id": getattr(call, "call_id", ""),
        "run_id": run_id,
        "seq": getattr(call, "seq", 0),
        "turns": getattr(call, "turns", 0),
        "tools_used": list(getattr(call, "tools_used", [])),
        "tokens_in": getattr(call, "tokens_in", 0),
        "tokens_out": getattr(call, "tokens_out", 0),
        "cost_usd": float(getattr(call, "cost_usd", 0.0)),
        "latency_ms": getattr(call, "latency_ms", 0),
        "prompt_redacted": getattr(call, "prompt_redacted", {}),
        "response": getattr(call, "response", {}),
        "guardrail_verdict": "accepted" if getattr(call, "accepted", True) else "rejected",
        "guardrail_reasons": list(getattr(call, "guardrail_reasons", [])),
    }


def _serialize_closure_record(cl: Any, run_id: str) -> dict[str, Any]:
    if isinstance(cl, dict):
        rec = dict(cl)
        rec["run_id"] = run_id
        return rec
    applied_at = getattr(cl, "applied_at", "")
    reversed_at = getattr(cl, "reversed_at", None)
    return {
        "closure_id": getattr(cl, "closure_id", ""),
        "run_id": run_id,
        "target": getattr(cl, "target", ""),
        "action": getattr(cl, "action", ""),
        "before": getattr(cl, "before", {}),
        "after": getattr(cl, "after", {}),
        "applied_at": applied_at.isoformat()
        if hasattr(applied_at, "isoformat")
        else str(applied_at),
        "reversed_at": reversed_at.isoformat()
        if reversed_at and hasattr(reversed_at, "isoformat")
        else None,
    }


class ReportPublisher:
    """Publishes completed reconciliation datasets and reports to persistence."""

    def __init__(self, store: StoragePort | None = None) -> None:
        self.store = store or MemoryStorageAdapter()

    def publish(
        self,
        dataset: GeneratedDataset,
        report: dict[str, Any],
        match_groups: list[Any] | None = None,
        link_decisions: list[Any] | None = None,
        agent_calls: list[Any] | None = None,
        closures: list[Any] | None = None,
        control_results: dict[str, Any] | None = None,
    ) -> None:
        """Persist full run data into relational tables."""
        run_id = str(report["run_id"])
        sanitized_report = _sanitize_secrets(report)

        # 1. Save Run
        self.store.save_run(run_id=run_id, report_data=sanitized_report, status="complete")

        # 2. Save Sources
        banks = [
            {
                "bank_id": b.bank_id,
                "posted_at": b.posted_at.isoformat(),
                "value_date": b.value_date.isoformat(),
                "amount_paise": b.amount_paise,
                "utr": b.utr,
                "narration": b.narration,
                "currency": b.currency,
            }
            for b in dataset.bank_txns
        ]
        payouts = [
            {
                "payout_id": p.payout_id,
                "created_at": p.created_at.isoformat(),
                "settled_at": p.settled_at.isoformat() if p.settled_at else None,
                "amount_paise": p.net_paise,
                "fee_paise": p.fee_paise,
                "tax_paise": p.tax_paise,
                "utr": p.utr,
                "status": p.status,
                "currency": p.currency,
            }
            for p in dataset.gateway_payouts
        ]
        ledgers = [
            {
                "ledger_id": el.ledger_id,
                "journal_id": el.journal_id,
                "entry_date": el.entry_date.isoformat(),
                "amount_paise": el.amount_paise,
                "account": el.account,
                "reference": el.reference,
                "currency": el.currency,
            }
            for el in dataset.ledger_entries
        ]
        self.store.save_sources(
            run_id=run_id,
            bank_txns=banks,
            payouts=payouts,
            ledger_entries=ledgers,
        )

        # 3. Save Truth Groups
        truth_records = [
            {
                "group_id": tg.group_id,
                "kind": tg.kind,
                "cohort": tg.cohort,
                "bank_ids": tg.bank_ids,
                "payout_ids": tg.payout_ids,
                "ledger_ids": tg.ledger_ids,
                "expected_outcome": tg.expected_outcome,
                "expected_tag": tg.expected_tag,
                "expected_bucket": tg.expected_bucket,
            }
            for tg in dataset.truth_groups
        ]
        self.store.save_truth_groups(run_id=run_id, truth_groups=truth_records)

        # 4. Save Exceptions
        exceptions = sanitized_report.get("exceptions", [])
        if isinstance(exceptions, list):
            self.store.save_exceptions(run_id=run_id, exceptions=exceptions)

        # 5. Save Match Groups
        if match_groups is not None:
            mg_records = [_serialize_match_group(mg) for mg in match_groups]
        else:
            from engine.core.matching.rules import DeterministicMatcher

            mres = DeterministicMatcher().match(
                dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
            )
            mg_records = [_serialize_match_group(mg) for mg in mres.matched_groups]
        self.store.save_match_groups(run_id=run_id, match_groups=mg_records)

        # 6. Save Link Decisions
        if link_decisions is not None:
            ld_records = [_serialize_link_decision(ld) for ld in link_decisions]
        else:
            from engine.core.grader import LinkGrader
            from engine.core.matching.blocker import build_candidate_space

            space = build_candidate_space(
                dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
            )
            grader = LinkGrader()
            raw_mgs = [mg for mg in (match_groups or []) if hasattr(mg, "bank_ids")]
            bp = grader.grade("bank_payout", space.bank_payout_pairs, raw_mgs, dataset.truth_links)
            pl = grader.grade(
                "payout_ledger", space.payout_ledger_pairs, raw_mgs, dataset.truth_links
            )
            ld_records = [_serialize_link_decision(ld) for ld in bp + pl]
        self.store.save_link_decisions(run_id=run_id, link_decisions=ld_records)

        # 7. Save Agent Calls
        if agent_calls is not None:
            agent_records = [_serialize_agent_call_record(c, run_id) for c in agent_calls]
        else:
            agent_records = []
        self.store.save_agent_calls(run_id=run_id, agent_calls=agent_records)

        # 8. Save Closures
        if closures is not None:
            closure_records = [_serialize_closure_record(c, run_id) for c in closures]
        else:
            from engine.app.closer import ClosureEngine
            from engine.core.classify import ExceptionClassifier

            raw_mgs_for_close = [
                mg for mg in (match_groups or []) if hasattr(mg, "bank_ids") and hasattr(mg, "kind")
            ]
            if not raw_mgs_for_close:
                from engine.core.matching.rules import DeterministicMatcher

                raw_mgs_for_close = (
                    DeterministicMatcher()
                    .match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)
                    .matched_groups
                )

            classified_exceptions = ExceptionClassifier().classify(
                bank_txns=dataset.bank_txns,
                gateway_payouts=dataset.gateway_payouts,
                ledger_entries=dataset.ledger_entries,
                matched_groups=raw_mgs_for_close,
            )
            closer = ClosureEngine()
            cres = closer.close(
                run_id=run_id,
                matched_groups=raw_mgs_for_close,
                exceptions=classified_exceptions,
                dry_run=False,
            )
            closure_records = [_serialize_closure_record(c, run_id) for c in cres.closures]

        self.store.save_closures(run_id=run_id, closures=closure_records)

        # 9. Save Control Results
        ctrls = control_results or sanitized_report.get("controls")
        if ctrls is not None and isinstance(ctrls, dict):
            cr_records: list[dict[str, Any]] = []
            for name, data in ctrls.items():
                if isinstance(data, dict):
                    cr_records.append(
                        {
                            "control_name": name,
                            "passed": bool(data.get("passed", True)),
                            "details": data,
                        }
                    )
            self.store.save_control_results(run_id=run_id, control_results=cr_records)

    def load_report(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve stored report by run ID."""
        return self.store.load_run(run_id=run_id)
