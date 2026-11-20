"""Live voice session tracker (metadata; real-time audio via provider)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

SESSIONS: Dict[str, dict] = {}


def start(user: str = "default", provider: str = "") -> dict:
    sid = uuid.uuid4().hex[:12]
    s = {"id": sid, "user": user, "provider": provider, "status": "listening",
         "started_at": time.time(), "ended_at": None, "turns": 0}
    SESSIONS[sid] = s
    return s


def update_status(sid: str, status: str) -> Optional[dict]:
    s = SESSIONS.get(sid)
    if not s:
        return None
    s["status"] = status
    return s


def add_turn(sid: str) -> Optional[dict]:
    s = SESSIONS.get(sid)
    if not s:
        return None
    s["turns"] += 1
    return s


def end(sid: str) -> Optional[dict]:
    s = SESSIONS.get(sid)
    if not s:
        return None
    s["status"] = "ended"
    s["ended_at"] = time.time()
    return s


def get(sid: str) -> Optional[dict]:
    return SESSIONS.get(sid)


def list_all(user: Optional[str] = None) -> List[dict]:
    out = list(SESSIONS.values())
    if user:
        out = [s for s in out if s["user"] == user]
    return out
