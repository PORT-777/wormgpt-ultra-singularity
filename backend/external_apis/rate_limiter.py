"""Shared per-service token-bucket rate limiter."""
from __future__ import annotations

import time
from typing import Dict, Tuple

from .config import config


class RateLimiter:
    def __init__(self, per_minute: int | None = None) -> None:
        self.rate = int(per_minute or config.rate_limit_per_min)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def allow(self, service: str) -> bool:
        now = time.time()
        tokens, last = self._buckets.get(service, (float(self.rate), now))
        refill = (now - last) * (self.rate / 60.0)
        tokens = min(float(self.rate), tokens + refill)
        if tokens < 1:
            self._buckets[service] = (tokens, now)
            return False
        self._buckets[service] = (tokens - 1, now)
        return True


limiter = RateLimiter()
