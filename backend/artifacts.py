"""Artifacts workspace (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "artifacts"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def create(name: str, kind: str, content: str, session_id: Optional[str] = None,
           mime: str = "text/plain") -> dict:
    aid = uuid.uuid4().hex[:12]
    art = {"id": aid, "name": name, "kind": kind, "content": content,
           "session_id": session_id, "mime": mime, "created_at": time.time(),
           "versions": [{"version": 1, "content": content, "created_at": time.time()}]}
    kv_store.set(MODULE, aid, art)
    return art


def get(aid: str) -> Optional[dict]:
    return kv_store.get(MODULE, aid)


def update(aid: str, content: str) -> Optional[dict]:
    art = kv_store.get(MODULE, aid)
    if not art:
        return None
    art["content"] = content
    v = len(art["versions"]) + 1
    art["versions"].append({"version": v, "content": content, "created_at": time.time()})
    kv_store.set(MODULE, aid, art)
    return art


def list_all(session_id: Optional[str] = None, kind: Optional[str] = None) -> List[dict]:
    out = _load()
    if session_id:
        out = [a for a in out if a["session_id"] == session_id]
    if kind:
        out = [a for a in out if a["kind"] == kind]
    return out


def delete(aid: str) -> bool:
    return kv_store.delete(MODULE, aid)
