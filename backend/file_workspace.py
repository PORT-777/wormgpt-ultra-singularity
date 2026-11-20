"""Unified file workspace (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional

import kv_store

MODULE = "file_workspace"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def register(path: str, kind: str = "upload", tags: Optional[List[str]] = None,
             session_id: Optional[str] = None, size: int = 0) -> dict:
    fid = uuid.uuid4().hex[:12]
    f = {"id": fid, "path": path, "kind": kind, "tags": tags or [],
         "session_id": session_id, "size": size, "created_at": time.time()}
    kv_store.set(MODULE, fid, f)
    return f


def get(fid: str) -> Optional[dict]:
    return kv_store.get(MODULE, fid)


def list_all(kind: Optional[str] = None, session_id: Optional[str] = None,
             tag: Optional[str] = None) -> List[dict]:
    out = _load()
    if kind:
        out = [f for f in out if f["kind"] == kind]
    if session_id:
        out = [f for f in out if f["session_id"] == session_id]
    if tag:
        out = [f for f in out if tag in f["tags"]]
    return out


def search(q: str) -> List[dict]:
    ql = q.lower()
    return [f for f in _load()
            if ql in f["path"].lower() or any(ql in t.lower() for t in f["tags"])]


def tag(fid: str, tags: List[str]) -> Optional[dict]:
    f = kv_store.get(MODULE, fid)
    if not f:
        return None
    for t in tags:
        if t not in f["tags"]:
            f["tags"].append(t)
    kv_store.set(MODULE, fid, f)
    return f


def delete(fid: str) -> bool:
    return kv_store.delete(MODULE, fid)
