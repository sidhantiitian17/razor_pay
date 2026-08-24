"""LLM client interface, request/response models, and usage accounting (§3.1, §6, R1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class UsageStats:
    """Token and dollar cost accounting for an LLM call (§3.1, check 3.9)."""

    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def to_dict(self) -> dict[str, object]:
        """Convert usage stats to dictionary."""
        return {
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 6),
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
        }


@dataclass
class LLMRequest:
    """Structured LLM invocation request with tool schemas."""

    messages: list[dict[str, object]]
    tools: list[dict[str, object]] = field(default_factory=list)
    temperature: float = 0.0
    max_tokens: int = 1024
    model: str = "claude-haiku-4-5-20251001"

    def to_sanitized_dict(self) -> dict[str, object]:
        """Return prompt and tool structure with all auth/secrets stripped (§3.10)."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "messages": self.messages,
            "tools": self.tools,
        }


@dataclass
class LLMResponse:
    """Structured LLM invocation response containing tool calls or message content."""

    tool_calls: list[dict[str, object]] = field(default_factory=list)
    content: str | None = None
    usage: UsageStats = field(default_factory=UsageStats)
    latency_ms: int = 0


class LLMClient(Protocol):
    """Protocol for LLM adapters (ports & adapters seam, §6)."""

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute model completion with tool support."""
        ...


class MockLLMClient:
    """Mock LLM client returning scripted responses and recording requests."""

    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.recorded_requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return next scripted response."""
        self.recorded_requests.append(request)
        if self._index < len(self._responses):
            res = self._responses[self._index]
            self._index += 1
            return res
        return LLMResponse(
            tool_calls=[],
            content="End of mock responses",
            usage=UsageStats(),
            latency_ms=0,
        )
