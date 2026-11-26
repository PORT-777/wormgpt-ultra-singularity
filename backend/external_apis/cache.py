"""Shared TTL response cache (stdlib fallback when cachetools is absent)."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

from .config import config


class TTLCache:
    def __init__(self, ttl: Optional[float] = None,
                 max_entries: Optional[int] = None) -> None:
        self.ttl = float(ttl if ttl is not None else config.cache_ttl_s)
        self.max_entries = int(max_entries or config.cache_max_entries)
        self._data: Dict[str, Tuple[float, Any]] = {}

    @staticmethod
    def make_key(name: str, action: str, payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(f"{name}:{action}:{raw}".encode()).hexdigest()

    def get(self, key: str) -> Any:
        item = self._data.get(key)
        if not item:
            return None
        expires, value = item
        if time.time() > expires:
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._data) >= self.max_entries:
            oldest = min(self._data, key=lambda k: self._data[k][0])
            self._data.pop(oldest, None)
        self._data[key] = (time.time() + self.ttl, value)

    def clear(self) -> None:
        self._data.clear()


cache = TTLCache()
