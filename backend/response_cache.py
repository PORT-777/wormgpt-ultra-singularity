"""Response cache (in-memory, TTL)."""
from __future__ import annotations

import json
import time
import hashlib
from typing import Dict, Any, Optional

CACHE: Dict[str, dict] = {}


def key_for(messages: list, model: str, params: dict = None) -> str:
    raw = json.dumps({"m": messages, "model": model, "p": params or {}}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def get(k: str) -> Optional[Any]:
    e = CACHE.get(k)
    if not e:
        return None
    if time.time() > e["expires"]:
        del CACHE[k]
        return None
    return e["value"]


def set(k: str, value: Any, ttl: int = 300) -> None:
    CACHE[k] = {"value": value, "expires": time.time() + ttl, "created": time.time()}


def invalidate(k: str) -> bool:
    return CACHE.pop(k, None) is not None


def clear() -> int:
    n = len(CACHE)
    CACHE.clear()
    return n


def stats() -> dict:
    return {"entries": len(CACHE)}
