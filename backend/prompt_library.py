"""Prompt library (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "prompt_library"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def create(title: str, content: str, tags: Optional[List[str]] = None,
           favorite: bool = False, model: Optional[str] = None) -> dict:
    p = {"id": uuid.uuid4().hex[:12], "title": title, "content": content,
         "tags": tags or [], "favorite": favorite, "model": model,
         "created_at": time.time(), "updated_at": time.time()}
    kv_store.set(MODULE, p["id"], p)
    return p


def update(pid: str, **fields) -> Optional[dict]:
    p = kv_store.get(MODULE, pid)
    if not p:
        return None
    for k, v in fields.items():
        if k in p and k != "id":
            p[k] = v
    p["updated_at"] = time.time()
    kv_store.set(MODULE, pid, p)
    return p


def delete(pid: str) -> bool:
    return kv_store.delete(MODULE, pid)


def get(pid: str) -> Optional[dict]:
    return kv_store.get(MODULE, pid)


def search(q: str = "", tag: Optional[str] = None,
           favorite_only: bool = False) -> List[dict]:
    out = _load()
    if q:
        ql = q.lower()
        out = [p for p in out if ql in p["title"].lower()
               or ql in p["content"].lower() or ql in " ".join(p["tags"]).lower()]
    if tag:
        out = [p for p in out if tag in p["tags"]]
    if favorite_only:
        out = [p for p in out if p["favorite"]]
    return list(out)


def export_all() -> List[dict]:
    return _load()


def import_many(items: List[dict]) -> int:
    n = 0
    for it in items:
        create(it.get("title", "untitled"), it.get("content", ""),
               tags=it.get("tags"), favorite=bool(it.get("favorite", False)),
               model=it.get("model"))
        n += 1
    return n
