"""Smart conversation context management.

Tracks token usage, detects context-window pressure, summarizes old turns.
"""
from __future__ import annotations

from typing import List, Dict, Optional

AVG_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // AVG_CHARS_PER_TOKEN)


def total_tokens(messages: List[Dict]) -> int:
    return sum(estimate_tokens(m.get("content", "") or "") for m in messages)


def needs_compaction(messages: List[Dict], context_window: int, threshold: float = 0.8) -> bool:
    return total_tokens(messages) > int(context_window * threshold)


def compact(messages: List[Dict], keep_last: int = 6) -> List[Dict]:
    """Keep system + last N turns; collapse middle into a summary placeholder."""
    if len(messages) <= keep_last + 1:
        return messages
    head = [m for m in messages if m.get("role") == "system"][:1]
    tail = messages[-keep_last:]
    middle = messages[len(head):len(messages) - keep_last]
    summary = {
        "role": "system",
        "content": f"[Summary of {len(middle)} earlier messages: context compacted to fit window.]",
    }
    return head + [summary] + tail


def build_context(messages: List[Dict], context_window: int) -> List[Dict]:
    if needs_compaction(messages, context_window):
        return compact(messages)
    return messages
