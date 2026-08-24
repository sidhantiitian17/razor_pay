"""Frozen Pydantic models for the reconciliation engine (§3.1).

All models are frozen (immutable after construction). Mutation raises.
Money is always integer paise (I1). Datetimes are always tz-aware UTC (I2).
"""

from __future__ import annotations

import enum

# Pydantic resolves string annotations (from __future__ import annotations)
# at runtime via typing.get_type_hints, so date/datetime must stay real
# names in module scope, not moved under TYPE_CHECKING, or model
# construction breaks. Deliberate override of ruff's TC003 suggestion.
from datetime import date, datetime  # noqa: TC003
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from engine.core.money import validate_paise
from engine.core.timewin import ensure_utc


def _check_paise(v: object) -> int:
    """Shared paise validator used by every money field below (I1).

    Delegates to engine.core.money.validate_paise so the float/int check
    exists in exactly one place instead of being duplicated per model.
    Pydantic v2 field validators only convert ValueError/AssertionError
    into a proper ValidationError — validate_paise raises TypeError (its
    own contract, exercised directly in tests/test_money.py), so that is
    re-raised as ValueError here or it would propagate uncaught instead
    of failing model construction cleanly.
    """
    try:
        return validate_paise(v)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(str(exc)) from exc


# --- Enumerations ---


class GroupKind(enum.StrEnum):
    """Group kinds with cardinality invariants (§3.2)."""

    SIMPLE = "simple"
    DUPLICATE_SET = "duplicate_set"
    REFUND_PAIR = "refund_pair"
    ORPHAN_BANK = "orphan_bank"
    ORPHAN_LEDGER = "orphan_ledger"


class ResolvedTag(enum.StrEnum):
    """Annotations on resolved groups — disjoint from ExceptionBucket (§3.6)."""

    CLEAN = "clean"
    DRIFT = "drift"
    TIMING_TOLERATED = "timing_tolerated"
    UTR_RECOVERED = "utr_recovered"
    REFUND = "refund"


class ExceptionBucket(enum.StrEnum):
    """Unresolved exception buckets — disjoint from ResolvedTag (§3.6)."""

    AMOUNT_MISMATCH = "amount_mismatch"
    FEE_MISMATCH = "fee_mismatch"
    TIMING_BREAK = "timing_break"
    MISSING_UTR = "missing_utr"
    DUPLICATE = "duplicate"
    REFUND_UNPAIRED = "refund_unpaired"
    ORPHAN_BANK = "orphan_bank"
    ORPHAN_LEDGER = "orphan_ledger"
    PARTIAL_GROUP = "partial_group"


UnresolvedBucket = ExceptionBucket


class CohortName(enum.StrEnum):
    """Generator cohort names (§3.5)."""

    CLEAN = "clean"
    DRIFT_TOLERATED = "drift_tolerated"
    DRIFT_EXCEPTION = "drift_exception"
    SKEW_TOLERATED = "skew_tolerated"
    SKEW_EXCEPTION = "skew_exception"
    MISSING_UTR_RECOVERABLE = "missing_utr_recoverable"
    MISSING_UTR_UNRECOVERABLE = "missing_utr_unrecoverable"
    DUPLICATE_PAYOUT = "duplicate_payout"
    REFUND_PAIR = "refund_pair"
    REFUND_UNPAIRED = "refund_unpaired"
    FEE_MISMATCH = "fee_mismatch"
    ORPHAN_BANK = "orphan_bank"
    ORPHAN_LEDGER = "orphan_ledger"


# --- Source Entities ---


class BankTxn(BaseModel):
    """A credit on the bank statement."""

    model_config = ConfigDict(frozen=True)

    bank_id: str
    posted_at: datetime
    value_date: date
    amount_paise: int
    utr: str | None
    narration: str
    currency: Literal["INR"] = "INR"

    @field_validator("amount_paise", mode="before")
    @classmethod
    def _validate_paise(cls, v: object) -> int:
        return _check_paise(v)

    @field_validator("posted_at")
    @classmethod
    def _validate_utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)


class GatewayPayout(BaseModel):
    """A settlement instruction from the gateway."""

    model_config = ConfigDict(frozen=True)

    payout_id: str
    created_at: datetime
    settled_at: datetime | None
    amount_paise: int  # GROSS
    fee_paise: int
    tax_paise: int
    utr: str | None
    status: Literal["processed", "reversed", "failed"]
    currency: Literal["INR"] = "INR"

    @field_validator("amount_paise", "fee_paise", "tax_paise", mode="before")
    @classmethod
    def _validate_paise(cls, v: object) -> int:
        return _check_paise(v)

    @field_validator("created_at")
    @classmethod
    def _validate_utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)

    @property
    def net_paise(self) -> int:
        """What actually hits the bank: gross - fee - tax (D3 fix)."""
        return self.amount_paise - self.fee_paise - self.tax_paise


class LedgerEntry(BaseModel):
    """One line of a journal set."""

    model_config = ConfigDict(frozen=True)

    ledger_id: str
    journal_id: str
    entry_date: date
    amount_paise: int  # signed
    account: Literal["bank", "settlements_receivable", "gateway_fees", "gateway_tax"]
    reference: str
    currency: Literal["INR"] = "INR"

    @field_validator("amount_paise", mode="before")
    @classmethod
    def _validate_paise(cls, v: object) -> int:
        return _check_paise(v)


# --- Truth Entities ---


class TruthGroup(BaseModel):
    """Ground truth grouping — never reachable from agent prompts (I12)."""

    model_config = ConfigDict(frozen=True)

    group_id: str
    kind: GroupKind
    cohort: CohortName
    bank_ids: list[str]
    payout_ids: list[str]
    ledger_ids: list[str]
    expected_outcome: Literal["resolved", "unresolved"]
    expected_tag: ResolvedTag | None = None
    expected_bucket: ExceptionBucket | None = None


class TruthLink(BaseModel):
    """Derived from TruthGroup — the grading atom."""

    model_config = ConfigDict(frozen=True)

    link_type: Literal["bank_payout", "payout_ledger"]
    left_id: str
    right_id: str
    is_match: bool


# --- Prediction Entities ---


class MatchGroup(BaseModel):
    """A predicted reconciliation group (D4 fix — replaces MatchTriple)."""

    model_config = ConfigDict(frozen=True)

    group_id: str
    kind: GroupKind
    bank_ids: list[str]
    payout_ids: list[str]
    ledger_ids: list[str]
    confidence: float
    source: Literal["deterministic", "agent"]
    fields_matched: list[str]
    tolerances_used: list[str]
    tag: ResolvedTag
    reason: str
    agent_turns: int


class ReconException(BaseModel):
    """An unresolved exception (D20 fix — renamed from Exception)."""

    model_config = ConfigDict(frozen=True)

    exception_id: str
    row_ids: list[str]
    bucket: ExceptionBucket
    severity: Literal["low", "medium", "high"]
    evidence: list[str]
    proposed_action: str
    status: Literal["open", "assigned", "resolved", "wont_fix"] = "open"
    assignee: str | None = None
    resolution_note: str | None = None


class LinkDecision(BaseModel):
    """Produced by the grader, one per candidate link."""

    model_config = ConfigDict(frozen=True)

    link_type: Literal["bank_payout", "payout_ledger"]
    left_id: str
    right_id: str
    predicted: bool
    truth: bool
    outcome: Literal["TP", "FP", "FN", "TN"]


class Closure(BaseModel):
    """The loop-closing write-back record."""

    model_config = ConfigDict(frozen=True)

    closure_id: str
    run_id: str
    target: str
    action: Literal["mark_reconciled", "post_adjustment", "open_exception"]
    before: dict[str, object]
    after: dict[str, object]
    applied_at: datetime
    reversed_at: datetime | None = None

    @field_validator("applied_at")
    @classmethod
    def _validate_utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)


class AgentCall(BaseModel):
    """Record of a single agent LLM call."""

    model_config = ConfigDict(frozen=True)

    call_id: str
    run_id: str
    seq: int
    turns: int
    tools_used: list[str]
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    prompt_redacted: dict[str, object]
    response: dict[str, object]
    guardrail_verdict: Literal["accepted", "rejected"]
    guardrail_reasons: list[str]


# --- Cardinality validation for GroupKind (I8) ---

_KIND_CARDINALITY: dict[GroupKind, tuple[int | None, int | None, int | None]] = {
    # (bank_count, payout_count, ledger_count) — None means >=1
    GroupKind.SIMPLE: (1, 1, 4),
    GroupKind.DUPLICATE_SET: (1, 2, 4),
    GroupKind.REFUND_PAIR: (None, 1, 8),  # bank can be 0 or 1
    GroupKind.ORPHAN_BANK: (1, 0, 0),
    GroupKind.ORPHAN_LEDGER: (0, 0, None),  # ledger >= 1
}


def validate_group_cardinality(
    kind: GroupKind,
    bank_count: int,
    payout_count: int,
    ledger_count: int,
) -> bool:
    """Validate that ID counts match the kind's cardinality invariant (I8).

    Args:
        kind: The group kind.
        bank_count: Number of bank IDs.
        payout_count: Number of payout IDs.
        ledger_count: Number of ledger IDs.

    Returns:
        True if cardinality is valid.

    Raises:
        ValueError: If cardinality violates the kind's rule.
    """
    expected = _KIND_CARDINALITY[kind]

    if kind == GroupKind.REFUND_PAIR:
        if bank_count not in (0, 1):
            raise ValueError(f"{kind.value}: bank_count must be 0 or 1, got {bank_count}")
        if payout_count != 1:
            raise ValueError(f"{kind.value}: payout_count must be 1, got {payout_count}")
        if ledger_count != 8:
            raise ValueError(f"{kind.value}: ledger_count must be 8, got {ledger_count}")
    elif kind == GroupKind.ORPHAN_LEDGER:
        if bank_count != 0:
            raise ValueError(f"{kind.value}: bank_count must be 0, got {bank_count}")
        if payout_count != 0:
            raise ValueError(f"{kind.value}: payout_count must be 0, got {payout_count}")
        if ledger_count < 1:
            raise ValueError(f"{kind.value}: ledger_count must be >= 1, got {ledger_count}")
    else:
        eb, ep, el = expected
        if eb is not None and bank_count != eb:
            raise ValueError(f"{kind.value}: bank_count must be {eb}, got {bank_count}")
        if ep is not None and payout_count != ep:
            raise ValueError(f"{kind.value}: payout_count must be {ep}, got {payout_count}")
        if el is not None and ledger_count != el:
            raise ValueError(f"{kind.value}: ledger_count must be {el}, got {ledger_count}")

    return True
