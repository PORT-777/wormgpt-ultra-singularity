"""Model context-window detection + honest trimming.

The gateway catalogues hundreds of models with very different context
sizes (8K .. 1M).  This module derives a realistic window from the model
id and trims conversation history before it reaches the provider, instead
of blindly assuming 8192 everywhere.

Nothing here calls a provider: it is pure, deterministic bookkeeping.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

DEFAULT_CONTEXT = 32768

# Ordered longest-first; first match wins.
_PATTERNS: List[tuple[re.Pattern[str], int]] = [
    (re.compile(r"(?<!\d)(1m|1000000|1048576)(?!\d)", re.I), 1048576),
    (re.compile(r"(?<!\d)(500k|500000|524288)(?!\d)", re.I), 500000),
    (re.compile(r"(?<!\d)(256k|262144|200k|200000)(?!\d)", re.I), 262144),
    (re.compile(r"(?<!\d)(128k|131072)(?!\d)", re.I), 131072),
    (re.compile(r"(?<!\d)(64k|65536)(?!\d)", re.I), 65536),
    (re.compile(r"(?<!\d)(32k|32768)(?!\d)", re.I), 32768),
    (re.compile(r"(?<!\d)(16k|16384)(?!\d)", re.I), 16384),
    (re.compile(r"(?<!\d)(8k|8192)(?!\d)", re.I), 8192),
    (re.compile(r"(?<!\d)(4k|4096)(?!\d)", re.I), 4096),
]

# Known small/reasoning models that don't advertise their size in the id.
_KNOWN = {
    "gpt-oss-120b": 131072,
    "gpt-oss-20b": 131072,
    "qwen3": 131072,
    "allam-2-7b": 32768,
    "llama-3": 128000,
    "nemotron-3.5-super-vl": 1000000,
    "ling-3.2-flash": 1048576,
    "gemma-4-31b": 262144,
    "gemma-4-26b": 262144,
}


def context_window_for(model_id: Optional[str], default: int = DEFAULT_CONTEXT) -> int:
    """Best-effort context window for a model id (never raises)."""
    mid = str(model_id or "").strip()
    if not mid:
        return default
    low = mid.lower()
    for key, size in _KNOWN.items():
        if key in low:
            return size
    for pat, size in _PATTERNS:
        if pat.search(low):
            return size
    return default


def _content_of(message: Any) -> str:
    if isinstance(message, dict):
        c = message.get("content")
        role = message.get("role") or message.get("type") or ""
    else:
        c = getattr(message, "content", "")
        role = str(getattr(message, "type", "") or "")
    if isinstance(c, str):
        text = c
    else:
        try:
            text = json.dumps(c, ensure_ascii=False, default=str)
        except Exception:
            text = str(c)
    return f"{role}:{text}"


def estimate_tokens(messages: List[Any]) -> int:
    """Rough token estimate (chars/4) — deliberately conservative."""
    total = 0
    for m in messages:
        total += len(_content_of(m))
    return total // 4


def trim_messages(messages: List[Any], context_window: int,
                  reserve: float = 0.85, min_keep: int = 2) -> tuple[List[Any], Dict[str, Any]]:
    """Drop oldest non-system turns until the estimate fits.

    Returns (messages, info).  Never mutates the input list.
    """
    total = estimate_tokens(messages)
    budget = max(1024, int(max(1, context_window) * reserve))
    info = {"context_window": int(context_window), "tokens": total,
            "budget": budget, "trimmed": False, "dropped": 0}
    if total <= budget:
        return list(messages), info

    system, rest = [], []
    for m in messages:
        if isinstance(m, dict):
            is_sys = (m.get("role") or m.get("type")) == "system"
        else:
            is_sys = str(getattr(m, "type", "")) == "system"
        (system if is_sys else rest).append(m)

    dropped = 0
    while rest and estimate_tokens(system + rest) > budget and \
            len(rest) > min_keep:
        rest.pop(0)
        dropped += 1
    info.update({"trimmed": dropped > 0, "dropped": dropped,
                 "tokens": estimate_tokens(system + rest)})
    return system + rest, info