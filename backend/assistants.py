"""Custom AI assistants (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "assistants"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def create(name: str, description: str = "", system_prompt: str = "",
           model: str = "", tools: Optional[List[str]] = None,
           kb_ids: Optional[List[str]] = None, memory_scope: str = "assistant") -> dict:
    aid = uuid.uuid4().hex[:12]
    a = {"id": aid, "name": name, "description": description,
         "system_prompt": system_prompt, "model": model,
         "tools": tools or [], "kb_ids": kb_ids or [],
         "memory_scope": memory_scope, "created_at": time.time()}
    kv_store.set(MODULE, aid, a)
    return a


def get(aid: str) -> Optional[dict]:
    return kv_store.get(MODULE, aid)


def list_all() -> List[dict]:
    return _load()


def update(aid: str, **fields) -> Optional[dict]:
    a = kv_store.get(MODULE, aid)
    if not a:
        return None
    for k, v in fields.items():
        if k in a and k != "id":
            a[k] = v
    kv_store.set(MODULE, aid, a)
    return a


def delete(aid: str) -> bool:
    return kv_store.delete(MODULE, aid)


def duplicate(aid: str) -> Optional[dict]:
    a = kv_store.get(MODULE, aid)
    if not a:
        return None
    return create(a["name"] + " (copy)", a["description"], a["system_prompt"],
                  a["model"], list(a["tools"]), list(a["kb_ids"]), a["memory_scope"])
