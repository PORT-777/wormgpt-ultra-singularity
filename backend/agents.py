"""AI agents (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

AGENTS_MOD = "agents"
TASKS_MOD = "agent_tasks"


def _load_agents() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(AGENTS_MOD)]


def _load_tasks() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(TASKS_MOD)]


def create_agent(name: str, role: str, system_prompt: str, model: str,
                 tools: Optional[List[str]] = None,
                 memory_scope: str = "agent", max_steps: int = 20) -> dict:
    aid = uuid.uuid4().hex[:12]
    a = {"id": aid, "name": name, "role": role, "system_prompt": system_prompt,
         "model": model, "tools": tools or [], "memory_scope": memory_scope,
         "max_steps": max_steps, "created_at": time.time()}
    kv_store.set(AGENTS_MOD, aid, a)
    return a


def get_agent(aid: str) -> Optional[dict]:
    return kv_store.get(AGENTS_MOD, aid)


def list_agents() -> List[dict]:
    return _load_agents()


def delete_agent(aid: str) -> bool:
    return kv_store.delete(AGENTS_MOD, aid)


def create_task(agent_id: str, goal: str) -> dict:
    tid = uuid.uuid4().hex[:12]
    t = {"id": tid, "agent_id": agent_id, "goal": goal, "status": "pending",
         "started_at": None, "finished_at": None, "steps": 0, "result": None,
         "error": None, "tool_calls": []}
    kv_store.set(TASKS_MOD, tid, t)
    return t


def update_task(tid: str, **fields) -> Optional[dict]:
    t = kv_store.get(TASKS_MOD, tid)
    if not t:
        return None
    for k, v in fields.items():
        if k in t:
            t[k] = v
    kv_store.set(TASKS_MOD, tid, t)
    return t


def get_task(tid: str) -> Optional[dict]:
    return kv_store.get(TASKS_MOD, tid)


def list_tasks(agent_id: Optional[str] = None) -> List[dict]:
    out = _load_tasks()
    if agent_id:
        out = [t for t in out if t["agent_id"] == agent_id]
    return out


def check_permission(agent: dict, tool: str) -> bool:
    return tool in (agent.get("tools") or [])
