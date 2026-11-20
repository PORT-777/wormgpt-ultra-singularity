"""Real persistent task records for the port777-task-manager plugin."""
from __future__ import annotations

import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Header, HTTPException

import kv_store

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
MODULE = "port777_tasks"


def _owner(x_user_id: Optional[str]) -> str:
    return str(x_user_id or "default_user")[:80]


def _record(owner: str, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
    kv_store.set(MODULE, key, value, owner=owner)
    return {"id": key, **value}


@router.get("")
async def list_tasks(status: str = "", x_user_id: Optional[str] = Header(None)):
    rows = kv_store.list_all(MODULE, owner=_owner(x_user_id))
    tasks = [{"id": r["key"], **(r["value"] or {})} for r in rows]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    tasks.sort(key=lambda t: (t.get("priority") or "", t.get("created") or 0))
    return {"tasks": tasks, "total": len(tasks)}


@router.post("")
async def create_task(payload: dict = Body(...), x_user_id: Optional[str] = Header(None)):
    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    owner = _owner(x_user_id)
    key = "task-" + secrets.token_hex(8)
    value = {
        "title": title[:300],
        "description": str(payload.get("description") or "")[:4000],
        "priority": str(payload.get("priority") or "normal").lower()[:20],
        "status": "open",
        "category": str(payload.get("category") or "general")[:60],
        "created": time.time(),
    }
    return _record(owner, key, value)


@router.patch("/{task_id}")
async def update_task(task_id: str, payload: dict = Body(...),
                      x_user_id: Optional[str] = Header(None)):
    owner = _owner(x_user_id)
    value = kv_store.get(MODULE, task_id)
    if not value:
        raise HTTPException(404, "task not found")
    for field in ("title", "description", "priority", "category"):
        if field in payload:
            value[field] = str(payload[field])[:4000]
    if "status" in payload:
        status = str(payload["status"]).lower()
        if status not in ("open", "done", "cancelled"):
            raise HTTPException(400, "invalid status")
        value["status"] = status
    value["updated"] = time.time()
    return _record(owner, task_id, value)


@router.delete("/{task_id}")
async def delete_task(task_id: str, x_user_id: Optional[str] = Header(None)):
    ok = kv_store.delete(MODULE, task_id)
    if not ok:
        raise HTTPException(404, "task not found")
    return {"deleted": True}
