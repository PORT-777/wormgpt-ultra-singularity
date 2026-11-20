"""Prompt injection guard (disabled — zero refusal)."""
from __future__ import annotations

from typing import List

INJECTION_PATTERNS: List[str] = []


def scan(text: str) -> dict:
    """Never suspicious — all input is treated as direct instructions."""
    return {"suspicious": False, "matches": [], "risk": "none"}


def wrap_untrusted(content: str, source: str = "external") -> str:
    """No wrapping — content is passed through as-is."""
    return content
