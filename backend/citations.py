"""Source citations (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "citations"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def attach(session_id: str, message_id: str, sources: List[dict]) -> List[dict]:
    out = []
    for s in sources:
        c = {"id": uuid.uuid4().hex[:12], "session_id": session_id,
             "message_id": message_id, "title": s.get("title", ""),
             "url": s.get("url", ""), "snippet": s.get("snippet", ""),
             "page": s.get("page"), "section": s.get("section"),
             "created_at": time.time()}
        kv_store.set(MODULE, c["id"], c)
        out.append(c)
    return out


def for_message(message_id: str) -> List[dict]:
    return [c for c in _load() if c["message_id"] == message_id]


def format_inline(sources: List[dict]) -> str:
    refs = []
    for i, s in enumerate(sources, 1):
        title = s.get("title") or s.get("url") or "source"
        refs.append(f"[{i}] {title}")
    return "\n".join(refs)
