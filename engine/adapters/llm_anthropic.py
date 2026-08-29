"""Live Anthropic API-backed LLM client (§3.1, §6, R1).

Wraps the official `anthropic` SDK so the same bounded multi-turn
tool-calling loop (`AgentRunner`) can run against a real Claude model
instead of the offline `HeuristicLLMClient` simulator. Selected
automatically by `engine.adapters.select.select_llm_client` when
`ANTHROPIC_API_KEY` is set and this optional dependency is installed
(`uv sync --extra llm`); the choice is always recorded in
`config.agent_backend` on the published report.

Requires `agent.py` to thread each turn's assistant tool-use blocks (with
stable ids) back into the message history — see `AgentRunner.resolve_residual`
— so a genuinely valid multi-turn Anthropic transcript can be reconstructed
turn over turn; without that threading a live model would only ever see an
incoherent fragment of the conversation from turn 2 onward.
"""

from __future__ import annotations

import time
from typing import Any

from engine.config import HAIKU_INPUT_COST_PER_MTOK, HAIKU_OUTPUT_COST_PER_MTOK, MODEL_NAME
from engine.ports.llm import LLMRequest, LLMResponse, UsageStats

SYSTEM_PROMPT = (
    "You are a bounded financial reconciliation agent resolving one "
    "unmatched record at a time. You may act only through the tools you "
    "are given: fetch_candidates, inspect_record, propose_match. Never "
    "invent a record id, amount, date, or field you have not fetched or "
    "inspected through those tools — a downstream deterministic guardrail "
    "independently verifies every id and field you cite, and will reject "
    "the proposal outright if anything doesn't check out. If no candidate "
    "in range is a confident match, call propose_match with a low "
    "confidence and an honest reason rather than guessing; a rejected, "
    "well-reasoned 'no match' is the correct outcome far more often than a "
    "confident wrong one."
)


class AnthropicLLMClient:
    """Live Claude client implementing the engine's `LLMClient` protocol."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = MODEL_NAME,
        cost_per_m_in: float = HAIKU_INPUT_COST_PER_MTOK,
        cost_per_m_out: float = HAIKU_OUTPUT_COST_PER_MTOK,
    ) -> None:
        # Imported lazily: `anthropic` is an optional extra ("llm"), not a
        # core dependency — the offline engine must import cleanly without it.
        import anthropic  # type: ignore[import-not-found]

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.cost_per_m_in = cost_per_m_in
        self.cost_per_m_out = cost_per_m_out
        self.recorded_requests: list[LLMRequest] = []

    def _calc_usage(self, tokens_in: int, tokens_out: int) -> UsageStats:
        cost = (tokens_in / 1_000_000.0) * self.cost_per_m_in + (
            tokens_out / 1_000_000.0
        ) * self.cost_per_m_out
        return UsageStats(tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=round(cost, 6))

    @staticmethod
    def _to_anthropic_messages(messages: list[dict[str, object]]) -> list[dict[str, Any]]:
        """Reconstruct a schema-valid Anthropic transcript.

        Rebuilds it from the engine's generic turn log (`agent.py` records
        user / assistant+tool_calls / tool entries — see module docstring).
        """
        out: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role == "assistant":
                blocks: list[dict[str, Any]] = []
                text = m.get("content")
                if isinstance(text, str) and text.strip():
                    blocks.append({"type": "text", "text": text})
                tool_calls_raw = m.get("tool_calls")
                tool_calls_list = tool_calls_raw if isinstance(tool_calls_raw, list) else []
                for tc in tool_calls_list:
                    if not isinstance(tc, dict):
                        continue
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": str(tc.get("id", "")),
                            "name": str(tc.get("name", "")),
                            "input": tc.get("arguments", {}),
                        }
                    )
                out.append({"role": "assistant", "content": blocks})
            elif role == "tool":
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": str(m.get("tool_use_id", "")),
                                "content": str(m.get("content", "")),
                            }
                        ],
                    }
                )
            else:
                out.append({"role": "user", "content": str(m.get("content", ""))})
        return out

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute one live completion turn against the Anthropic Messages API."""
        self.recorded_requests.append(request)

        t0 = time.perf_counter()
        response = self._client.messages.create(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=SYSTEM_PROMPT,
            tools=[
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t["input_schema"],
                }
                for t in request.tools
            ],
            messages=self._to_anthropic_messages(request.messages),
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        tool_calls: list[dict[str, object]] = []
        text_content: str | None = None
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(
                    {"id": block.id, "name": block.name, "arguments": dict(block.input)}
                )
            elif block.type == "text" and block.text.strip():
                text_content = block.text

        usage = self._calc_usage(
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
        )
        return LLMResponse(
            tool_calls=tool_calls,
            content=text_content,
            usage=usage,
            latency_ms=latency_ms,
        )
