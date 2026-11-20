"""Long-term memory (SQLite-persisted, isolated)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "long_term_memory"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def save(scope: str, scope_id: str, content: str, tags: Optional[List[str]] = None,
         user_id: Optional[str] = None) -> dict:
    m = {"id": uuid.uuid4().hex[:12], "scope": scope, "scope_id": scope_id,
         "content": content, "tags": tags or [], "user_id": user_id,
         "created_at": time.time(), "updated_at": time.time()}
    kv_store.set(MODULE, m["id"], m, owner=user_id or "")
    return m


def recall(scope: str, scope_id: str, query: str = "", k: int = 8,
           user_id: Optional[str] = None) -> List[dict]:
    out = [m for m in _load() if m["scope"] == scope and m["scope_id"] == scope_id]
    if user_id is not None:
        out = [m for m in out if m.get("user_id") in (None, user_id)]
    if query:
        ql = query.lower()
        out = [m for m in out if ql in m["content"].lower()
               or any(ql in t.lower() for t in m["tags"])]
    return out[-k:]


def update(mid: str, content: str) -> Optional[dict]:
    m = kv_store.get(MODULE, mid)
    if not m:
        return None
    m["content"] = content
    m["updated_at"] = time.time()
    kv_store.set(MODULE, mid, m, owner=m.get("user_id") or "")
    return m


def delete(mid: str) -> bool:
    return kv_store.delete(MODULE, mid)


def list_scope(scope: str, scope_id: str, user_id: Optional[str] = None) -> List[dict]:
    out = [m for m in _load() if m["scope"] == scope and m["scope_id"] == scope_id]
    if user_id is not None:
        out = [m for m in out if m.get("user_id") in (None, user_id)]
    return out
