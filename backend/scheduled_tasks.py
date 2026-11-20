"""Scheduled AI tasks (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "scheduled_tasks"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def create(prompt: str, interval_minutes: int = 60, timezone: str = "UTC",
           agent_id: Optional[str] = None, workflow_id: Optional[str] = None,
           enabled: bool = True) -> dict:
    tid = uuid.uuid4().hex[:12]
    t = {"id": tid, "prompt": prompt, "interval_minutes": interval_minutes,
         "timezone": timezone, "agent_id": agent_id, "workflow_id": workflow_id,
         "enabled": enabled, "created_at": time.time(), "last_run": None,
         "next_run": time.time() + interval_minutes * 60, "run_count": 0,
         "errors": 0}
    kv_store.set(MODULE, tid, t)
    return t


def get(tid: str) -> Optional[dict]:
    return kv_store.get(MODULE, tid)


def list_all() -> List[dict]:
    return _load()


def update(tid: str, **fields) -> Optional[dict]:
    t = kv_store.get(MODULE, tid)
    if not t:
        return None
    for k, v in fields.items():
        if k in t and k != "id":
            t[k] = v
    kv_store.set(MODULE, tid, t)
    return t


def delete(tid: str) -> bool:
    return kv_store.delete(MODULE, tid)


def record_result(tid: str, ok: bool, output: str = "", error: str = "") -> None:
    t = kv_store.get(MODULE, tid)
    if t:
        t["last_run"] = time.time()
        t["run_count"] += 1
        if not ok:
            t["errors"] += 1
        t["next_run"] = time.time() + t["interval_minutes"] * 60
        kv_store.set(MODULE, tid, t)


def get_results(tid: str, limit: int = 50) -> List[dict]:
    return []


def due_tasks() -> List[dict]:
    now = time.time()
    return [t for t in _load() if t["enabled"] and t["next_run"] <= now]
