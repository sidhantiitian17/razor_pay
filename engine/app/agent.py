"""Bounded multi-turn agent loop with tool dispatch and guardrail integration (§3.1, §6, R1, D17).

Enforces schema-validated tool calling, strict turn limits, truth isolation (I12),
and comprehensive cost/latency/turn telemetry.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.core.guardrail import (
    GuardrailConfig,
    GuardrailValidator,
    MatchProposal,
)
from engine.core.models import (
    GroupKind,
    MatchGroup,
    ResolvedTag,
)

if TYPE_CHECKING:
    from engine.core.matching.blocker import CandidateSpace
    from engine.core.models import BankTxn, GatewayPayout, LedgerEntry
    from engine.ports.llm import LLMClient

AGENT_TOOLS_SCHEMA: list[dict[str, object]] = [
    {
        "name": "fetch_candidates",
        "description": "Fetch candidate matches for a given bank or payout record.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bank_id": {"type": "string", "description": "Bank transaction ID"},
                "payout_id": {"type": "string", "description": "Gateway payout ID"},
            },
        },
    },
    {
        "name": "inspect_record",
        "description": "Inspect full fields of a record without ground truth labels.",
        "input_schema": {
            "type": "object",
            "required": ["record_id"],
            "properties": {
                "record_id": {"type": "string", "description": "ID of the record to inspect"},
            },
        },
    },
    {
        "name": "propose_match",
        "description": "Propose a resolved match group across bank, payout, and ledger lines.",
        "input_schema": {
            "type": "object",
            "required": [
                "bank_id",
                "payout_id",
                "ledger_ids",
                "confidence",
                "fields_matched",
                "reason",
            ],
            "properties": {
                "bank_id": {"type": "string"},
                "payout_id": {"type": "string"},
                "ledger_ids": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "fields_matched": {"type": "array", "items": {"type": "string"}},
                "reason": {"type": "string"},
            },
        },
    },
]


class FreeTextResponseError(Exception):
    """Raised when an LLM turn emits free text without a schema-valid tool call."""


class TurnLimitExceededError(Exception):
    """Raised when the agent loop exceeds MAX_TURNS without terminating (§3.2, D17)."""


@dataclass
class AgentCallResult:
    """Telemetry and outcome from an agent resolution call."""

    call_id: str
    run_id: str
    turns: int
    tools_used: list[str]
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    prompt_redacted: dict[str, object]
    response: dict[str, object]
    accepted: bool
    guardrail_reasons: list[str] = field(default_factory=list)
    proposed_group: MatchGroup | None = None


class AgentRunner:
    """Executes the bounded multi-turn tool loop (§3.1, R1)."""

    def __init__(
        self,
        llm_client: LLMClient,
        guardrail_config: GuardrailConfig | None = None,
        max_turns: int = 6,
        enabled_tools: set[str] | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.guardrail_config = guardrail_config or GuardrailConfig()
        self.max_turns = max_turns
        self.enabled_tools = enabled_tools or {
            "fetch_candidates",
            "inspect_record",
            "propose_match",
        }

    def get_tools_schema(self) -> list[dict[str, object]]:
        """Return the subset of tools enabled for this runner."""
        return [t for t in AGENT_TOOLS_SCHEMA if t["name"] in self.enabled_tools]

    def resolve_residual(
        self,
        row_id: str,
        bank_txns: list[BankTxn],
        gateway_payouts: list[GatewayPayout],
        ledger_entries: list[LedgerEntry],
        candidate_space: CandidateSpace,
    ) -> AgentCallResult:
        """Execute bounded multi-turn loop to resolve an unmatched residual."""
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        validator = GuardrailValidator(
            config=self.guardrail_config,
            bank_txns=bank_txns,
            gateway_payouts=gateway_payouts,
            ledger_entries=ledger_entries,
        )

        bank_by_id = {b.bank_id: b for b in bank_txns}
        payout_by_id = {p.payout_id: p for p in gateway_payouts}
        ledger_by_id = {entry.ledger_id: entry for entry in ledger_entries}

        # Initial prompt context (ensuring no truth / cohort labels leak, I12)
        initial_context = f"Resolve unmatched residual row: {row_id}."
        messages: list[dict[str, object]] = [
            {
                "role": "user",
                "content": initial_context,
            }
        ]

        turns = 0
        tools_used: list[str] = []
        tokens_in = 0
        tokens_out = 0
        cost_usd = 0.0
        latency_ms = 0

        last_response_dict: dict[str, object] = {}

        from engine.ports.llm import LLMRequest

        while turns < self.max_turns:
            tools = self.get_tools_schema()
            req = LLMRequest(
                messages=messages,
                tools=tools,
            )

            resp = self.llm_client.complete(req)

            tokens_in += resp.usage.tokens_in
            tokens_out += resp.usage.tokens_out
            cost_usd += resp.usage.cost_usd
            latency_ms += resp.latency_ms

            if not resp.tool_calls and resp.content:
                raise FreeTextResponseError(
                    f"Model emitted free text without tool call: {resp.content}"
                )

            if not resp.tool_calls:
                break

            # Assign a stable id to every tool_use block in this turn before
            # recording the assistant's turn, so the paired tool-result
            # message (and any real LLM adapter reconstructing a valid
            # Anthropic-style transcript) can reference it unambiguously.
            for tool_call in resp.tool_calls:
                if not tool_call.get("id"):
                    tool_call["id"] = f"toolu_{uuid.uuid4().hex[:12]}"

            # Record the assistant's own turn (its tool_use blocks) in the
            # transcript. The heuristic/mock clients only ever look at the
            # tail of `messages`, so this is transparent to them; a live LLM
            # adapter needs it to reconstruct a schema-valid multi-turn call.
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": resp.tool_calls,
                    "content": resp.content,
                }
            )

            for tool_call in resp.tool_calls:
                turns += 1
                tool_name = str(tool_call.get("name"))
                tool_use_id = str(tool_call.get("id", ""))
                args = tool_call.get("arguments", {})
                if not isinstance(args, dict):
                    args = {}

                tools_used.append(tool_name)
                last_response_dict = {
                    "tool_calls": resp.tool_calls,
                    "content": resp.content,
                }

                if tool_name == "fetch_candidates":
                    # Query candidate space
                    b_id = str(args.get("bank_id", ""))
                    p_id = str(args.get("payout_id", ""))
                    candidates: list[dict[str, object]] = []
                    if b_id:
                        for bp in candidate_space.bank_payout_pairs:
                            if bp[0] == b_id:
                                candidates.append({"payout_id": bp[1]})
                    if p_id:
                        for pl in candidate_space.payout_ledger_pairs:
                            if pl[0] == p_id:
                                led = ledger_by_id.get(pl[1])
                                cand: dict[str, object] = {"ledger_id": pl[1]}
                                if led is not None:
                                    cand["reference"] = led.reference
                                    cand["amount_paise"] = led.amount_paise
                                candidates.append(cand)

                    messages.append(
                        {
                            "role": "tool",
                            "name": tool_name,
                            "tool_use_id": tool_use_id,
                            "content": str({"candidates": candidates}),
                        }
                    )

                elif tool_name == "inspect_record":
                    rec_id = str(args.get("record_id", ""))
                    info: dict[str, object] = {}
                    if rec_id in bank_by_id:
                        b = bank_by_id[rec_id]
                        info = {
                            "bank_id": b.bank_id,
                            "amount_paise": b.amount_paise,
                            "value_date": str(b.value_date),
                            "narration": b.narration,
                            "utr": b.utr,
                        }
                    elif rec_id in payout_by_id:
                        p = payout_by_id[rec_id]
                        info = {
                            "payout_id": p.payout_id,
                            "amount_paise": p.amount_paise,
                            "fee_paise": p.fee_paise,
                            "tax_paise": p.tax_paise,
                            "net_paise": p.net_paise,
                            "settled_at": str(p.settled_at),
                            "utr": p.utr,
                        }
                    elif rec_id in ledger_by_id:
                        entry = ledger_by_id[rec_id]
                        info = {
                            "ledger_id": entry.ledger_id,
                            "journal_id": entry.journal_id,
                            "account": entry.account,
                            "amount_paise": entry.amount_paise,
                            "reference": entry.reference,
                        }

                    messages.append(
                        {
                            "role": "tool",
                            "name": tool_name,
                            "tool_use_id": tool_use_id,
                            "content": str(info),
                        }
                    )

                elif tool_name == "propose_match":
                    proposal = MatchProposal(
                        bank_id=str(args.get("bank_id", "")),
                        payout_id=str(args.get("payout_id", "")),
                        ledger_ids=[str(lid) for lid in args.get("ledger_ids", [])],
                        confidence=float(args.get("confidence", 0.0)),
                        fields_matched=[str(f) for f in args.get("fields_matched", [])],
                        reason=str(args.get("reason", "")),
                    )

                    verdict = validator.validate(proposal)

                    if verdict.status == "accepted":
                        mg = MatchGroup(
                            group_id=f"MG-AG-{uuid.uuid4().hex[:6]}",
                            kind=GroupKind.SIMPLE,
                            bank_ids=[proposal.bank_id],
                            payout_ids=[proposal.payout_id],
                            ledger_ids=proposal.ledger_ids,
                            confidence=proposal.confidence,
                            source="agent",
                            fields_matched=proposal.fields_matched,
                            tolerances_used=[],
                            tag=ResolvedTag.CLEAN,
                            reason=proposal.reason,
                            agent_turns=turns,
                        )
                        return AgentCallResult(
                            call_id=call_id,
                            run_id=run_id,
                            turns=turns,
                            tools_used=tools_used,
                            tokens_in=tokens_in,
                            tokens_out=tokens_out,
                            cost_usd=cost_usd,
                            latency_ms=latency_ms,
                            prompt_redacted={"messages": messages},
                            response=last_response_dict,
                            accepted=True,
                            guardrail_reasons=[],
                            proposed_group=mg,
                        )

                    return AgentCallResult(
                        call_id=call_id,
                        run_id=run_id,
                        turns=turns,
                        tools_used=tools_used,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                        prompt_redacted={"messages": messages},
                        response=last_response_dict,
                        accepted=False,
                        guardrail_reasons=verdict.reasons,
                        proposed_group=None,
                    )

        if turns >= self.max_turns:
            raise TurnLimitExceededError(f"Agent loop exceeded maximum turns ({self.max_turns})")

        return AgentCallResult(
            call_id=call_id,
            run_id=run_id,
            turns=turns,
            tools_used=tools_used,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            prompt_redacted={"messages": messages},
            response=last_response_dict,
            accepted=False,
            guardrail_reasons=["max_turns_exhausted"],
            proposed_group=None,
        )


def compute_agent_turn_stats(
    call_stats: list[dict[str, int]],
) -> dict[str, float | int]:
    """Compute agent_turns mean, max, and single_turn_fraction (§5.1, R1, check 3.13)."""
    if not call_stats:
        return {
            "mean": 0.0,
            "max": 0,
            "single_turn_fraction": 0.0,
        }

    turns_list = [c["turns"] for c in call_stats]
    total_calls = len(turns_list)
    mean_turns = sum(turns_list) / total_calls
    max_turns = max(turns_list)
    single_turn_count = sum(1 for t in turns_list if t == 1)
    single_turn_fraction = single_turn_count / total_calls

    return {
        "mean": round(mean_turns, 2),
        "max": max_turns,
        "single_turn_fraction": round(single_turn_fraction, 4),
    }
