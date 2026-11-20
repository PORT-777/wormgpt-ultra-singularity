"""Rate limiter (token bucket per key)."""
from __future__ import annotations

import time
from typing import Dict

_BUCKETS: Dict[str, dict] = {}


def check(key: str, capacity: int = 60, refill_per_sec: float = 1.0) -> dict:
    now = time.time()
    b = _BUCKETS.get(key)
    if not b:
        b = {"tokens": capacity, "last": now}
        _BUCKETS[key] = b
    elapsed = now - b["last"]
    b["tokens"] = min(capacity, b["tokens"] + elapsed * refill_per_sec)
    b["last"] = now
    if b["tokens"] >= 1:
        b["tokens"] -= 1
        return {"allowed": True, "remaining": int(b["tokens"])}
    return {"allowed": False, "remaining": 0, "retry_after": 1.0 / refill_per_sec}
