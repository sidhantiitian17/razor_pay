"""LLM client backend selection (§3.1, §6).

Chooses a live Anthropic-backed client when `ANTHROPIC_API_KEY` is set and
the optional `anthropic` package is installed; otherwise falls back to the
deterministic offline heuristic simulator (`HeuristicLLMClient`). Whichever
backend is chosen is always returned alongside its name so the caller can
record it verbatim in the published report's `config.agent_backend` field —
this selection never happens silently, and a reviewer reading a report never
has to guess whether "agent" numbers came from a real model or a stand-in.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from engine.adapters.llm_heuristic import HeuristicLLMClient

if TYPE_CHECKING:
    from engine.ports.llm import LLMClient

AgentBackend = str  # "live" | "heuristic"


def select_llm_client() -> tuple[LLMClient, AgentBackend]:
    """Return `(client, backend_name)` for the default (no explicit override) case.

    `backend_name` is `"live"` when a real Anthropic client was constructed,
    `"heuristic"` when the offline simulator was used instead (no API key
    configured, or the optional `anthropic` package is not installed).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            from engine.adapters.llm_anthropic import AnthropicLLMClient

            return AnthropicLLMClient(api_key=api_key), "live"
        except ImportError:
            # `anthropic` extra not installed — fall back rather than crash
            # a run; the report will honestly say "heuristic", not "live".
            pass
    return HeuristicLLMClient(), "heuristic"
