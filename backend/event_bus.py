"""Simple in-process event bus for cross-module notifications."""
from __future__ import annotations

from typing import Callable, Dict, List

SUBSCRIBERS: Dict[str, List[Callable]] = {}


def subscribe(event: str, cb: Callable) -> None:
    SUBSCRIBERS.setdefault(event, []).append(cb)


def unsubscribe(event: str, cb: Callable) -> None:
    if event in SUBSCRIBERS:
        SUBSCRIBERS[event] = [c for c in SUBSCRIBERS[event] if c is not cb]


def publish(event: str, payload: dict = None) -> int:
    n = 0
    for cb in list(SUBSCRIBERS.get(event, [])):
        try:
            cb(payload or {})
            n += 1
        except Exception:
            pass
    # wildcard
    for cb in list(SUBSCRIBERS.get("*", [])):
        try:
            cb({"event": event, **(payload or {})})
            n += 1
        except Exception:
            pass
    return n


def events() -> List[str]:
    return list(SUBSCRIBERS.keys())
