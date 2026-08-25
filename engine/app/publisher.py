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


class ReportPublisher:
    """Publishes completed reconciliation datasets and reports to persistence."""

    def __init__(self, store: StoragePort | None = None) -> None:
        self.store = store or MemoryStorageAdapter()

    def publish(
        self,
        dataset: GeneratedDataset,
        report: dict[str, Any],
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

        # 5. Save Control Results
        if control_results is not None:
            cr_records: list[dict[str, Any]] = []
            for name, data in control_results.items():
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
