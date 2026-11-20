"""Saved searches."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

SEARCHES: Dict[str, dict] = {}


def save(name: str, query: str, filters: dict = None, user: str = "default") -> dict:
    sid = uuid.uuid4().hex[:12]
    s = {"id": sid, "name": name, "query": query, "filters": filters or {},
         "user": user, "created_at": time.time()}
    SEARCHES[sid] = s
    return s


def list_all(user: Optional[str] = None) -> List[dict]:
    out = list(SEARCHES.values())
    if user:
        out = [s for s in out if s["user"] == user]
    return out


def get(sid: str) -> Optional[dict]:
    return SEARCHES.get(sid)


def delete(sid: str) -> bool:
    return SEARCHES.pop(sid, None) is not None
