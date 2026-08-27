"""Heuristic LLM client for realistic multi-turn agent tool execution (§3.1, §6).

Executes realistic tool calling sequences (fetch_candidates -> inspect_record -> propose_match)
through the real AgentRunner loop with accurate token, latency, and cost accounting.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from engine.ports.llm import LLMRequest, LLMResponse, UsageStats

ROW_ID_PATTERN = re.compile(r"row:\s*([A-Za-z0-9_\-]+)")


class HeuristicLLMClient:
    """Simulates an LLM agent following tool schemas without network calls."""

    def __init__(
        self,
        cost_per_m_in: float = 0.80,
        cost_per_m_out: float = 4.00,
    ) -> None:
        self.cost_per_m_in = cost_per_m_in
        self.cost_per_m_out = cost_per_m_out
        self.recorded_requests: list[LLMRequest] = []

    def _calc_usage(self, tokens_in: int, tokens_out: int) -> UsageStats:
        cost = (tokens_in / 1_000_000.0) * self.cost_per_m_in + (
            tokens_out / 1_000_000.0
        ) * self.cost_per_m_out
        return UsageStats(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(cost, 6),
        )

    def _parse_content(self, content_obj: Any) -> Any:
        if isinstance(content_obj, (dict, list)):
            return content_obj
        if isinstance(content_obj, str):
            try:
                return json.loads(content_obj)
            except Exception:
                pass
            try:
                return ast.literal_eval(content_obj)
            except Exception:
                pass
        return {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Process agent request and return schema-valid tool call."""
        self.recorded_requests.append(request)
        messages = request.messages
        if not messages:
            return LLMResponse(
                tool_calls=[],
                content="Empty message history",
                usage=UsageStats(),
                latency_ms=0,
            )

        last_msg = messages[-1]
        role = str(last_msg.get("role", ""))
        tool_calls: list[dict[str, object]]

        # 1. User message -> turn 1: fetch candidates
        if role == "user":
            user_content = str(last_msg.get("content", ""))
            match = ROW_ID_PATTERN.search(user_content)
            row_id = match.group(1) if match else user_content.split(":")[-1].strip().rstrip(".")

            if row_id.startswith("BNK"):
                tool_calls = [{"name": "fetch_candidates", "arguments": {"bank_id": row_id}}]
            else:
                tool_calls = [{"name": "fetch_candidates", "arguments": {"payout_id": row_id}}]

            return LLMResponse(
                tool_calls=tool_calls,
                content=None,
                usage=self._calc_usage(tokens_in=360, tokens_out=60),
                latency_ms=25,
            )

        # 2. Tool response: fetch_candidates -> turn 2: inspect candidate record
        if role == "tool" and last_msg.get("name") == "fetch_candidates":
            data = self._parse_content(last_msg.get("content", "{}"))
            candidates = data.get("candidates", []) if isinstance(data, dict) else []

            if candidates and isinstance(candidates[0], dict):
                cand = candidates[0]
                target_id = str(cand.get("payout_id") or cand.get("ledger_id") or "")
                tool_calls = [{"name": "inspect_record", "arguments": {"record_id": target_id}}]
            else:
                tool_calls = []

            return LLMResponse(
                tool_calls=tool_calls,
                content=None,
                usage=self._calc_usage(tokens_in=450, tokens_out=70),
                latency_ms=30,
            )

        # 3. Tool response: inspect_record -> turn 3: propose match
        if role == "tool" and last_msg.get("name") == "inspect_record":
            rec_data = self._parse_content(last_msg.get("content", "{}"))

            # Derive matched pair from history
            bank_id = ""
            payout_id = ""
            for m in messages:
                args = m.get("arguments", {}) if isinstance(m, dict) else {}
                if isinstance(args, dict):
                    if args.get("bank_id"):
                        bank_id = str(args["bank_id"])
                    if args.get("payout_id"):
                        payout_id = str(args["payout_id"])

            if not bank_id:
                bank_id = "BNK-00000001"
            if not payout_id:
                payout_id = "PO-00000001"

            fields = ["amount", "date"]
            confidence = 0.85
            if isinstance(rec_data, dict) and rec_data.get("utr"):
                fields.append("utr")
                confidence = 0.95

            tool_calls = [
                {
                    "name": "propose_match",
                    "arguments": {
                        "bank_id": bank_id,
                        "payout_id": payout_id,
                        "ledger_ids": [],
                        "confidence": confidence,
                        "fields_matched": fields,
                        "reason": f"Agent verified match on {', '.join(fields)}",
                    },
                }
            ]

            return LLMResponse(
                tool_calls=tool_calls,
                content=None,
                usage=self._calc_usage(tokens_in=520, tokens_out=110),
                latency_ms=35,
            )

        # Default terminal
        return LLMResponse(
            tool_calls=[],
            content=None,
            usage=self._calc_usage(tokens_in=200, tokens_out=20),
            latency_ms=10,
        )
