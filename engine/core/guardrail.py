"""Guardrail validation rules and proposal safety filters (§3.6, R8, D15, check 3.7).

Validates agent match proposals against confidence, multi-field, hallucination,
amount drift, and timing skew thresholds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from engine.core.models import BankTxn, GatewayPayout, LedgerEntry

FORBIDDEN_TRUTH_PATTERNS = [
    re.compile(r"\bcohort\s*=", re.IGNORECASE),
    re.compile(r"\btruth\s*=", re.IGNORECASE),
    re.compile(r"\bground_truth\b", re.IGNORECASE),
    re.compile(r"\bexpected_outcome\s*=", re.IGNORECASE),
    re.compile(r"\bexpected_tag\s*=", re.IGNORECASE),
    re.compile(r"\bexpected_bucket\s*=", re.IGNORECASE),
]


def detect_truth_leak(messages: list[dict[str, object]] | str) -> bool:
    """Detect whether prompt or message payload leaks forbidden ground-truth labels (I12)."""
    import json

    text = json.dumps(messages) if not isinstance(messages, str) else messages
    return any(pat.search(text) for pat in FORBIDDEN_TRUTH_PATTERNS)


@dataclass(frozen=True)
class GuardrailConfig:
    """Configurable thresholds for proposal acceptance."""

    min_confidence: float = 0.70
    min_fields: int = 2
    max_drift_paise: int = 50
    max_skew_days: int = 2
    max_pct_delta: float = 0.01

    def to_dict(self) -> dict[str, object]:
        """Convert guardrail config to dictionary."""
        return {
            "min_confidence": self.min_confidence,
            "min_fields": self.min_fields,
            "max_drift_paise": self.max_drift_paise,
            "max_skew_days": self.max_skew_days,
            "max_pct_delta": self.max_pct_delta,
        }


@dataclass(frozen=True)
class MatchProposal:
    """Agent proposal for resolving a residual match group."""

    bank_id: str
    payout_id: str
    ledger_ids: list[str]
    confidence: float
    fields_matched: list[str]
    reason: str


@dataclass(frozen=True)
class GuardrailVerdict:
    """Outcome of guardrail evaluation."""

    status: Literal["accepted", "rejected"]
    reasons: list[str] = field(default_factory=list)


class GuardrailValidator:
    """Deterministic validator enforcing guardrail safety constraints (§3.6)."""

    def __init__(
        self,
        config: GuardrailConfig,
        bank_txns: list[BankTxn],
        gateway_payouts: list[GatewayPayout],
        ledger_entries: list[LedgerEntry],
    ) -> None:
        self.config = config
        self.bank_by_id = {b.bank_id: b for b in bank_txns}
        self.payout_by_id = {p.payout_id: p for p in gateway_payouts}
        self.ledger_by_id = {entry.ledger_id: entry for entry in ledger_entries}

    def validate(self, proposal: MatchProposal) -> GuardrailVerdict:
        """Evaluate match proposal against all guardrail rules."""
        reasons: list[str] = []

        # 1. Confidence threshold check
        if proposal.confidence < self.config.min_confidence:
            reasons.append("low_confidence")

        # 2. Multi-field requirement check (>= min_fields)
        if len(proposal.fields_matched) < self.config.min_fields:
            reasons.append("single_field")

        # 3. Non-existent / hallucinated ID check
        bank = self.bank_by_id.get(proposal.bank_id)
        payout = self.payout_by_id.get(proposal.payout_id)
        missing_ledgers = any(lid not in self.ledger_by_id for lid in proposal.ledger_ids)

        if bank is None or payout is None or missing_ledgers:
            reasons.append("hallucinated_id")
            return GuardrailVerdict(status="rejected", reasons=reasons)

        # 4. Amount delta tolerance check
        drift = abs(bank.amount_paise - payout.net_paise)
        pct_tol = int(payout.net_paise * self.config.max_pct_delta)
        if drift > self.config.max_drift_paise and drift > pct_tol:
            reasons.append("delta_too_large")

        # 5. Timing skew tolerance check
        if payout.settled_at is not None:
            days = abs((bank.value_date - payout.settled_at.date()).days)
            if days > self.config.max_skew_days:
                reasons.append("skew_too_large")

        status: Literal["accepted", "rejected"] = "accepted" if not reasons else "rejected"
        return GuardrailVerdict(status=status, reasons=reasons)
