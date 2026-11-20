"""Per-model system prompts: independent, toggleable, persisted in memory."""
from __future__ import annotations

from typing import Dict, Optional

PROMPTS: Dict[str, dict] = {}


def set_prompt(model: str, prompt: str, enabled: bool = True) -> dict:
    rec = {"model": model, "prompt": prompt, "enabled": enabled,
           "updated_at": __import__("time").time()}
    PROMPTS[model] = rec
    return rec


def get_prompt(model: str) -> Optional[dict]:
    return PROMPTS.get(model)


def toggle(model: str, enabled: bool) -> Optional[dict]:
    r = PROMPTS.get(model)
    if not r:
        return None
    r["enabled"] = enabled
    return r


def delete(model: str) -> bool:
    return PROMPTS.pop(model, None) is not None


def resolve(model: str, route: str = "", explicit: str = "") -> str:
    if explicit and explicit.strip():
        return explicit
    r = PROMPTS.get(model) or PROMPTS.get(route)
    if r and r.get("enabled"):
        return r["prompt"]
    return ""


def list_all() -> list:
    return list(PROMPTS.values())
