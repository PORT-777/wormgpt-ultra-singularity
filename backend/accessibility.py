"""Accessibility preferences (SQLite-persisted)."""
from __future__ import annotations

from typing import Dict, Any

import kv_store

MODULE = "accessibility"
DEFAULTS = {"reduced_motion": False, "high_contrast": False,
            "font_scale": 1.0, "keyboard_nav": True, "screen_reader": False}


def _load(user: str) -> Dict[str, Any]:
    v = kv_store.get(MODULE, user)
    if not isinstance(v, dict):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update(v)
    return out


def get(user: str = "default") -> Dict[str, Any]:
    return _load(user)


def set(user: str, **fields) -> Dict[str, Any]:
    p = _load(user)
    for k, v in fields.items():
        if k in p:
            p[k] = v
    kv_store.set(MODULE, user, p)
    return dict(p)


def all_prefs() -> Dict[str, Dict[str, Any]]:
    return {e["key"]: e["value"] for e in kv_store.list_all(MODULE)}
