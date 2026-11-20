"""Typing indicators / presence for chat sessions."""
from __future__ import annotations

import time
from typing import Dict, List

TYPING: Dict[str, Dict[str, float]] = {}


def set_typing(session_id: str, user: str, ttl: float = 5.0) -> None:
    TYPING.setdefault(session_id, {})[user] = time.time() + ttl


def clear_typing(session_id: str, user: str) -> None:
    if session_id in TYPING and user in TYPING[session_id]:
        del TYPING[session_id][user]


def who_is_typing(session_id: str) -> List[str]:
    now = time.time()
    d = TYPING.get(session_id, {})
    active = [u for u, exp in d.items() if exp > now]
    # cleanup
    TYPING[session_id] = {u: exp for u, exp in d.items() if exp > now}
    return active
