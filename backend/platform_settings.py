"""Platform settings (SQLite-persisted)."""
from __future__ import annotations

from typing import Any

import kv_store

MODULE = "platform_settings"
DEFAULTS = {"theme": "red-black", "default_language": "en",
            "default_model_route": "auto", "memory_enabled": False,
            "file_index_enabled": False, "mcp_enabled": False}


def _load() -> dict:
    v = kv_store.get(MODULE, "settings")
    if not isinstance(v, dict):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update(v)
    return out


def get(key: str, default: Any = None):
    return _load().get(key, default)


def set(key: str, value) -> None:
    s = _load()
    s[key] = value
    kv_store.set(MODULE, "settings", s)


def all_settings() -> dict:
    return _load()


def update_many(updates: dict) -> None:
    s = _load()
    s.update(updates)
    kv_store.set(MODULE, "settings", s)
