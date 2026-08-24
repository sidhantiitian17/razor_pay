"""Engine configuration constants."""

from __future__ import annotations

# Pricing — from Anthropic API pricing page
# https://docs.anthropic.com/en/docs/about-claude/pricing
HAIKU_INPUT_COST_PER_MTOK: float = 0.80
HAIKU_OUTPUT_COST_PER_MTOK: float = 4.00
PRICING_LAST_VERIFIED: str = "2026-08-24"
MODEL_NAME: str = "claude-haiku-4-5-20251001"

# Engine defaults
DEFAULT_TEMPERATURE: float = 0.0
DEFAULT_MAX_TURNS: int = 6
DEFAULT_CONCURRENCY: int = 4
DEFAULT_N: int = 100

# Tolerances (§3.4)
DRIFT_PAISE_TOLERANCE: int = 49
SKEW_DAYS_TOLERANCE: int = 2
PCT_DELTA_TOLERANCE: float = 0.01

# Guardrail defaults (§4.4)
GUARDRAIL_MIN_CONFIDENCE: float = 0.70
GUARDRAIL_MIN_FIELDS: int = 2

# Safety caps (D17)
MAX_TURNS: int = 6
MAX_RESIDUALS: int = 500
MAX_LLM_CALLS: int = 200
MAX_PROMPT_BYTES: int = 500_000
MAX_LLM_COST_USD: float = 5.0

# Schema
SCHEMA_VERSION: str = "1.0.0"
ENGINE_VERSION: str = "0.1.0"
