"""User management (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "users"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def create(username: str, role: str = "user", email: str = "") -> dict:
    uid = uuid.uuid4().hex[:12]
    u = {"id": uid, "username": username, "role": role, "email": email,
         "status": "active", "created_at": time.time()}
    kv_store.set(MODULE, uid, u)
    return u


def get(uid: str) -> Optional[dict]:
    return kv_store.get(MODULE, uid)


def by_username(username: str) -> Optional[dict]:
    for u in _load():
        if u["username"] == username:
            return u
    return None


def list_all(role: Optional[str] = None) -> List[dict]:
    out = _load()
    if role:
        out = [u for u in out if u["role"] == role]
    return out


def set_role(uid: str, role: str) -> Optional[dict]:
    u = kv_store.get(MODULE, uid)
    if not u:
        return None
    u["role"] = role
    kv_store.set(MODULE, uid, u)
    return u


def set_status(uid: str, status: str) -> Optional[dict]:
    u = kv_store.get(MODULE, uid)
    if not u:
        return None
    u["status"] = status
    kv_store.set(MODULE, uid, u)
    return u


def delete(uid: str) -> bool:
    return kv_store.delete(MODULE, uid)
