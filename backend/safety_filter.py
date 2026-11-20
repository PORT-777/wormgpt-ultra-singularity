"""Content inspection without enforcement.

Patterns are reported for diagnostics/tests only. Nothing is blocked or
redacted: zero-refusal mode keeps all content flowing to the engine unchanged.
"""
from __future__ import annotations

import re
from typing import List

PATTERNS: List[str] = []


def add_pattern(p: str) -> None:
    if p and p not in PATTERNS:
        PATTERNS.append(p)


def check(text: str) -> dict:
    value = str(text or "")
    matches = [p for p in PATTERNS if re.search(p, value, re.IGNORECASE)]
    return {"flagged": bool(matches), "matches": matches}


def redact(text: str, replacement: str = "[REDACTED]") -> str:
    """No-op: nothing is redacted in zero-refusal mode."""
    return text
