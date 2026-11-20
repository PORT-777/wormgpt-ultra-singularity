"""Audit log: full-access action trail."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

AUDIT: List[dict] = []


def record(action: str, actor: str = "system", details: Optional[dict] = None,
           session_id: Optional[str] = None) -> dict:
    e = {"id": uuid.uuid4().hex[:12], "action": action, "actor": actor,
         "details": details or {}, "session_id": session_id,
         "timestamp": time.time()}
    AUDIT.append(e)
    if len(AUDIT) > 10000:
        del AUDIT[:1000]
    return e


def list_all(limit: int = 100, action: Optional[str] = None,
             actor: Optional[str] = None) -> List[dict]:
    out = AUDIT
    if action:
        out = [e for e in out if e["action"] == action]
    if actor:
        out = [e for e in out if e["actor"] == actor]
    return list(reversed(out[-limit:]))


def clear() -> int:
    global AUDIT
    n = len(AUDIT)
    AUDIT = []
    return n
