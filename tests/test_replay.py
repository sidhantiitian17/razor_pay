"""Tests for deterministic cassette recording and replay (check 3.6, 3.10, ADR-001)."""

from engine.adapters.llm_replay import (
    BlockingTransportAsserter,
    Cassette,
    ReplayLLMClient,
)
from engine.ports.llm import LLMRequest, LLMResponse, UsageStats


def test_replay_zero_network_calls() -> None:
    """Check 3.6: Replay makes zero network calls; blocking transport asserts it."""
    cassette = Cassette(
        entries=[
            (
                LLMRequest(
                    messages=[{"role": "user", "content": "test"}],
                    tools=[{"name": "fetch_candidates", "description": "Fetch candidates"}],
                ),
                LLMResponse(
                    tool_calls=[
                        {
                            "name": "fetch_candidates",
                            "arguments": {"bank_id": "BNK-000001"},
                        }
                    ],
                    usage=UsageStats(tokens_in=100, tokens_out=50, cost_usd=0.0001),
                    latency_ms=120,
                ),
            )
        ]
    )

    with BlockingTransportAsserter.assert_no_network():
        client = ReplayLLMClient(cassette=cassette)
        res1 = client.complete(
            LLMRequest(
                messages=[{"role": "user", "content": "test"}],
                tools=[{"name": "fetch_candidates", "description": "Fetch candidates"}],
            )
        )
        res2 = client.complete(
            LLMRequest(
                messages=[{"role": "user", "content": "test"}],
                tools=[{"name": "fetch_candidates", "description": "Fetch candidates"}],
            )
        )

        assert res1 == res2
        assert res1.tool_calls[0]["name"] == "fetch_candidates"
        assert client.network_calls_made == 0


def test_cassette_no_auth_headers() -> None:
    """Check 3.10: Cassettes store only sanitized prompts, no auth or api keys."""
    cassette = Cassette(
        entries=[
            (
                LLMRequest(
                    messages=[{"role": "user", "content": "test prompt"}],
                    tools=[],
                ),
                LLMResponse(
                    tool_calls=[],
                    usage=UsageStats(tokens_in=50, tokens_out=20, cost_usd=0.00005),
                    latency_ms=80,
                ),
            )
        ]
    )
    serialized = cassette.to_json()
    assert "authorization" not in serialized.lower()
    assert "x-api-key" not in serialized.lower()
    assert "bearer" not in serialized.lower()
