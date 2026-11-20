"""Conversation memory: summaries, linking related conversations."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

SUMMARIES: Dict[str, dict] = {}
LINKS: Dict[str, List[str]] = {}


def summarize(session_id: str, summary: str, message_range: Optional[tuple] = None) -> dict:
    sid = uuid.uuid4().hex[:12]
    rec = {"id": sid, "session_id": session_id, "summary": summary,
           "range": message_range, "created_at": time.time()}
    SUMMARIES[sid] = rec
    return rec


def for_session(session_id: str) -> List[dict]:
    return [s for s in SUMMARIES.values() if s["session_id"] == session_id]


def link(a: str, b: str) -> None:
    LINKS.setdefault(a, [])
    if b not in LINKS[a]:
        LINKS[a].append(b)
    LINKS.setdefault(b, [])
    if a not in LINKS[b]:
        LINKS[b].append(a)


def related(session_id: str) -> List[str]:
    return list(LINKS.get(session_id, []))
