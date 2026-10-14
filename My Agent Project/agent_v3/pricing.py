"""Token prices and cost math. PRICING is copied from the homework's usage.py (text rates only)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# USD per 1M tokens.
PRICING: dict[str, dict[str, float]] = {
    "gpt-6-astra": {"input": 10.00, "cached": 1.00, "output": 50.00},
    "gpt-5.6-sol": {"input": 4.00, "cached": 0.40, "output": 20.00},
    "gpt-5.6-terra": {"input": 2.00, "cached": 0.20, "output": 12.00},
    "gpt-5.6-luna": {"input": 0.20, "cached": 0.02, "output": 1.20},
    "gpt-5.6-cyber": {"input": 12.50, "cached": 1.25, "output": 75.00},
    "gpt-daybreak-blue-latest": {"input": 4.00, "cached": 0.40, "output": 20.00},
    "gpt-daybreak-red-latest": {"input": 12.50, "cached": 1.25, "output": 75.00},
    "chat-latest": {"input": 5.00, "cached": 0.50, "output": 30.00},
    "gpt-5.4": {"input": 2.25, "cached": 0.225, "output": 18.00},
    "gpt-5.4-pro": {"input": 27.00, "cached": 0.0, "output": 216.00},
    "gpt-5.3-chat-latest": {"input": 1.75, "cached": 0.175, "output": 14.00},
    "gpt-5.3-codex": {"input": 1.75, "cached": 0.175, "output": 14.00},
    "gpt-5.2": {"input": 1.75, "cached": 0.175, "output": 14.00},
    "gpt-5.2-chat-latest": {"input": 1.75, "cached": 0.175, "output": 14.00},
    "gpt-5.2-codex": {"input": 1.75, "cached": 0.175, "output": 14.00},
    "gpt-5.2-pro": {"input": 21.00, "cached": 0.0, "output": 168.00},
    "gpt-5.1": {"input": 1.25, "cached": 0.125, "output": 10.00},
    "gpt-5.1-chat-latest": {"input": 1.25, "cached": 0.125, "output": 10.00},
    "gpt-5.1-codex": {"input": 1.25, "cached": 0.125, "output": 10.00},
    "gpt-5.1-codex-max": {"input": 1.25, "cached": 0.125, "output": 10.00},
    "gpt-5": {"input": 1.25, "cached": 0.125, "output": 10.00},
    "gpt-5-chat-latest": {"input": 1.25, "cached": 0.125, "output": 10.00},
    "gpt-5-codex": {"input": 1.25, "cached": 0.125, "output": 10.00},
    "gpt-5-pro": {"input": 15.00, "cached": 0.0, "output": 120.00},
    "gpt-5-mini": {"input": 0.25, "cached": 0.025, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "cached": 0.005, "output": 0.40},
    "gpt-4.1": {"input": 2.00, "cached": 0.50, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "cached": 0.10, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "cached": 0.025, "output": 0.40},
}


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0          # includes cached_tokens
    cached_tokens: int = 0
    output_tokens: int = 0         # includes reasoning_tokens
    reasoning_tokens: int = 0

    @classmethod
    def from_api(cls, usage: Any) -> "Usage":
        """From a Responses API `usage` (dict or SDK object); missing fields count as 0."""
        def get(obj, key):
            if obj is None:
                return None
            return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)
        return cls(input_tokens=get(usage, "input_tokens") or 0,
                   cached_tokens=get(get(usage, "input_tokens_details"), "cached_tokens") or 0,
                   output_tokens=get(usage, "output_tokens") or 0,
                   reasoning_tokens=get(get(usage, "output_tokens_details"), "reasoning_tokens") or 0)


def rates_for(model: str) -> dict[str, float] | None:
    """Exact match, else the longest table entry that prefixes a dated snapshot name (gpt-5-mini-2025-…)."""
    if model in PRICING:
        return PRICING[model]
    prefixes = [m for m in PRICING if model.startswith(m + "-")]
    return PRICING[max(prefixes, key=len)] if prefixes else None


def cost_usd(model: str, usage: Usage) -> float | None:
    """uncached×input + cached×cached + output×output (reasoning is already inside output). None if unknown."""
    rates = rates_for(model)
    if rates is None:
        return None
    uncached = max(usage.input_tokens - usage.cached_tokens, 0)
    return (uncached * rates["input"] + usage.cached_tokens * rates["cached"]
            + usage.output_tokens * rates["output"]) / 1_000_000
