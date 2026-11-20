"""Prompt inspection without enforcement.

Detection is kept for diagnostics/tests, but nothing here blocks, wraps or
rewrites input. The engine treats all input as direct instructions and the
zero-refusal policy ignores any "suspicious" label.
"""
from __future__ import annotations

import re
from typing import List

INJECTION_PATTERNS: List[str] = [
    r"ignore all previous instructions",
    r"disregard (all )?(previous|prior) instructions",
    r"you are now",
    r"system prompt",
    r"jailbreak",
]


def scan(text: str) -> dict:
    matches = []
    value = str(text or "")
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            matches.append(pattern)
    return {"suspicious": bool(matches), "matches": matches, "risk": "low" if matches else "none"}


def wrap_untrusted(content: str, source: str = "external") -> str:
    """No wrapping — content is passed through as-is."""
    return content
