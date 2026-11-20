"""Cost estimation with updatable model pricing."""
from __future__ import annotations

from typing import Dict, Optional

PRICING: Dict[str, dict] = {}


def set_pricing(model: str, input_per_1k: float, output_per_1k: float,
                cached_input_per_1k: float = 0.0) -> None:
    PRICING[model] = {"input_per_1k": input_per_1k,
                      "output_per_1k": output_per_1k,
                      "cached_input_per_1k": cached_input_per_1k}


def get_pricing(model: str) -> Optional[dict]:
    return PRICING.get(model)


def estimate(model: str, input_tokens: int, output_tokens: int,
             cached_tokens: int = 0) -> dict:
    p = PRICING.get(model, {"input_per_1k": 0.0, "output_per_1k": 0.0,
                            "cached_input_per_1k": 0.0})
    inp = input_tokens * p["input_per_1k"] / 1000.0
    out = output_tokens * p["output_per_1k"] / 1000.0
    cached = cached_tokens * p["cached_input_per_1k"] / 1000.0
    return {"model": model, "input_cost": round(inp, 6),
            "output_cost": round(out, 6), "cached_cost": round(cached, 6),
            "total": round(inp + out + cached, 6)}


def all_pricing() -> dict:
    return dict(PRICING)
