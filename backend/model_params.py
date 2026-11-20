"""Per-model parameters store."""
from __future__ import annotations

from typing import Dict, Optional

PARAMS: Dict[str, dict] = {}


def set_params(model: str, temperature: Optional[float] = None,
               max_tokens: Optional[int] = None, top_p: Optional[float] = None,
               reasoning_effort: Optional[str] = None, extra: Optional[dict] = None) -> dict:
    rec = PARAMS.get(model, {"model": model})
    if temperature is not None:
        rec["temperature"] = temperature
    if max_tokens is not None:
        rec["max_tokens"] = max_tokens
    if top_p is not None:
        rec["top_p"] = top_p
    if reasoning_effort is not None:
        rec["reasoning_effort"] = reasoning_effort
    if extra:
        rec.setdefault("extra", {}).update(extra)
    PARAMS[model] = rec
    return rec


def get_params(model: str) -> dict:
    return dict(PARAMS.get(model, {"model": model}))


def delete(model: str) -> bool:
    return PARAMS.pop(model, None) is not None


def list_all() -> list:
    return list(PARAMS.values())


def build_kwargs(model: str) -> dict:
    p = PARAMS.get(model, {})
    out = {}
    if "temperature" in p:
        out["temperature"] = p["temperature"]
    if "max_tokens" in p:
        out["max_tokens"] = p["max_tokens"]
    if "top_p" in p:
        out["top_p"] = p["top_p"]
    if "reasoning_effort" in p:
        out["reasoning_effort"] = p["reasoning_effort"]
    if "extra" in p:
        out.update(p["extra"])
    return out
