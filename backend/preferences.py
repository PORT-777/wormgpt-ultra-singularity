"""User preferences + memory preferences store."""
from __future__ import annotations

from typing import Dict, Any, Optional

PREFS: Dict[str, Dict[str, Any]] = {}
MEMORY_PREFS: Dict[str, Dict[str, Any]] = {}


def set_pref(user: str, key: str, value: Any) -> None:
    PREFS.setdefault(user, {})[key] = value


def get_pref(user: str, key: str, default: Any = None) -> Any:
    return PREFS.get(user, {}).get(key, default)


def all_prefs(user: str) -> Dict[str, Any]:
    return dict(PREFS.get(user, {}))


def delete_pref(user: str, key: str) -> bool:
    if user in PREFS and key in PREFS[user]:
        del PREFS[user][key]
        return True
    return False


def set_memory_pref(user: str, key: str, value: Any) -> None:
    MEMORY_PREFS.setdefault(user, {})[key] = value


def get_memory_pref(user: str, key: str, default: Any = None) -> Any:
    return MEMORY_PREFS.get(user, {}).get(key, default)


def memory_enabled(user: str) -> bool:
    return bool(MEMORY_PREFS.get(user, {}).get("enabled", True))
