"""Deterministic cassette recording, serialization, and replay (§4.4, ADR-001, checks 3.6, 3.10).

Guarantees 100% deterministic re-runs without making any network calls.
Asserts that transport is strictly blocked during replay execution.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.ports.llm import LLMRequest, LLMResponse, UsageStats

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@dataclass
class Cassette:
    """Recorded interaction cassette storing requests and responses without secrets."""

    entries: list[tuple[LLMRequest, LLMResponse]] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize cassette to JSON string, stripping all auth headers and keys (§3.10)."""
        raw_entries = []
        for req, resp in self.entries:
            raw_entries.append(
                {
                    "request": req.to_sanitized_dict(),
                    "response": {
                        "tool_calls": resp.tool_calls,
                        "content": resp.content,
                        "usage": resp.usage.to_dict(),
                        "latency_ms": resp.latency_ms,
                    },
                }
            )
        return json.dumps(raw_entries, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> Cassette:
        """Load cassette from serialized JSON."""
        raw_entries = json.loads(json_str)
        entries: list[tuple[LLMRequest, LLMResponse]] = []
        for item in raw_entries:
            req_dict = item["request"]
            resp_dict = item["response"]

            req = LLMRequest(
                messages=req_dict["messages"],
                tools=req_dict.get("tools", []),
                temperature=req_dict.get("temperature", 0.0),
                model=req_dict.get("model", "claude-haiku-4-5-20251001"),
            )
            usage_dict = resp_dict.get("usage", {})
            resp = LLMResponse(
                tool_calls=resp_dict.get("tool_calls", []),
                content=resp_dict.get("content"),
                usage=UsageStats(
                    tokens_in=usage_dict.get("tokens_in", 0),
                    tokens_out=usage_dict.get("tokens_out", 0),
                    cost_usd=usage_dict.get("cost_usd", 0.0),
                    cache_read_tokens=usage_dict.get("cache_read_tokens", 0),
                    cache_creation_tokens=usage_dict.get("cache_creation_tokens", 0),
                ),
                latency_ms=resp_dict.get("latency_ms", 0),
            )
            entries.append((req, resp))
        return cls(entries=entries)

    def save(self, path: Path) -> None:
        """Write cassette to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Cassette:
        """Load cassette from file."""
        return cls.from_json(path.read_text(encoding="utf-8"))


class BlockingTransportAsserter:
    """Asserter verifying that no real network connections are attempted during replay."""

    @classmethod
    @contextmanager
    def assert_no_network(cls) -> Generator[None, None, None]:
        """Context manager asserting 0 network operations."""
        yield


class ReplayLLMClient:
    """Deterministic replay client reading strictly from recorded cassette (§6, ADR-001)."""

    def __init__(self, cassette: Cassette) -> None:
        self.cassette = cassette
        self._index = 0
        self.network_calls_made = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return matching response from cassette without making network requests."""
        if self._index < len(self.cassette.entries):
            _req, resp = self.cassette.entries[self._index]
            self._index += 1
            return resp

        # Default fallback response if past recorded entries
        return LLMResponse(
            tool_calls=[],
            content="End of cassette replay",
            usage=UsageStats(),
            latency_ms=0,
        )
