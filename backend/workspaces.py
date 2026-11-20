"""Workspace system (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

MODULE = "workspaces"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def _by_id(wid: str) -> Optional[dict]:
    return kv_store.get(MODULE, wid)


def create(name: str, owner: str = "admin") -> dict:
    wid = uuid.uuid4().hex[:12]
    ws = {"id": wid, "name": name, "owner": owner, "members": [owner],
          "created_at": time.time(), "resources": {"conversations": [], "files": [],
          "knowledge_bases": [], "assistants": [], "agents": [], "workflows": [],
          "artifacts": []}}
    kv_store.set(MODULE, wid, ws, owner=owner)
    return ws


def get(wid: str) -> Optional[dict]:
    return _by_id(wid)


def list_all(owner: Optional[str] = None) -> List[dict]:
    out = _load()
    if owner:
        out = [w for w in out if owner in w.get("members", [])]
    return out


def add_member(wid: str, user: str) -> bool:
    ws = _by_id(wid)
    if not ws or user in ws["members"]:
        return False
    ws["members"].append(user)
    kv_store.set(MODULE, wid, ws, owner=ws["owner"])
    return True


def remove_member(wid: str, user: str) -> bool:
    ws = _by_id(wid)
    if not ws or user == ws["owner"]:
        return False
    if user in ws["members"]:
        ws["members"].remove(user)
        kv_store.set(MODULE, wid, ws, owner=ws["owner"])
        return True
    return False


def link_resource(wid: str, rtype: str, rid: str) -> bool:
    ws = _by_id(wid)
    if not ws or rtype not in ws["resources"]:
        return False
    if rid not in ws["resources"][rtype]:
        ws["resources"][rtype].append(rid)
        kv_store.set(MODULE, wid, ws, owner=ws["owner"])
    return True


def delete(wid: str) -> bool:
    return kv_store.delete(MODULE, wid)
