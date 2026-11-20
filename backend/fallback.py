"""Smart fallback & retry with exponential backoff + jitter."""
from __future__ import annotations

import random
import time
from typing import Callable, Any, Optional, List


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    exp = min(cap, base * (2 ** attempt))
    jitter = random.uniform(0, exp * 0.3)
    return exp + jitter


def retry(func: Callable, *args, max_attempts: int = 3, retry_on: tuple = (Exception,),
         on_retry: Optional[Callable] = None, **kwargs) -> Any:
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except retry_on as e:
            last_exc = e
            if attempt < max_attempts - 1:
                delay = backoff_delay(attempt)
                if on_retry:
                    on_retry(attempt, e, delay)
                time.sleep(delay)
    raise last_exc  # type: ignore


class FallbackChain:
    def __init__(self, providers: List[Callable]):
        self.providers = providers

    def run(self, *args, **kwargs) -> Any:
        last_exc = None
        for p in self.providers:
            try:
                return p(*args, **kwargs)
            except Exception as e:
                last_exc = e
                continue
        if last_exc:
            raise last_exc
        raise RuntimeError("no providers")
