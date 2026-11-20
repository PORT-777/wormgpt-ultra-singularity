"""Content safety filter (disabled — zero refusal)."""
from __future__ import annotations

from typing import List

PATTERNS: List[str] = []


def add_pattern(p: str) -> None:
    """No-op: safety patterns are disabled by zero-refusal policy."""


def check(text: str) -> dict:
    """Always clear — no content is ever flagged or blocked."""
    return {"flagged": False, "matches": []}


def redact(text: str, replacement: str = "[REDACTED]") -> str:
    """No-op: nothing is redacted."""
    return text
