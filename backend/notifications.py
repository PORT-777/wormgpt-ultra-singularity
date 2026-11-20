"""In-app notification center (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "notifications"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def push(kind: str, title: str, body: str = "", meta: Optional[dict] = None) -> dict:
    n = {"id": uuid.uuid4().hex[:12], "kind": kind, "title": title,
         "body": body, "meta": meta or {}, "created_at": time.time(), "read": False}
    kv_store.set(MODULE, n["id"], n)
    return n


def list_all(kind: Optional[str] = None, unread_only: bool = False) -> List[dict]:
    out = _load()
    if kind:
        out = [n for n in out if n["kind"] == kind]
    if unread_only:
        out = [n for n in out if not n["read"]]
    return out


def mark_read(nid: str) -> bool:
    n = kv_store.get(MODULE, nid)
    if not n:
        return False
    n["read"] = True
    kv_store.set(MODULE, nid, n)
    return True


def delete(nid: str) -> bool:
    return kv_store.delete(MODULE, nid)


def clear_read() -> int:
    items = _load()
    n = 0
    for it in items:
        if it.get("read"):
            kv_store.delete(MODULE, it["id"])
            n += 1
    return n
