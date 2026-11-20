"""Message edit history / regenerate support."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

VERSIONS: Dict[str, List[dict]] = {}


def record_edit(message_id: str, content: str, edited_by: str = "user") -> dict:
    v = {"id": uuid.uuid4().hex[:12], "message_id": message_id,
         "content": content, "edited_by": edited_by, "created_at": time.time()}
    VERSIONS.setdefault(message_id, []).append(v)
    return v


def history(message_id: str) -> List[dict]:
    return list(VERSIONS.get(message_id, []))


def latest(message_id: str) -> Optional[dict]:
    vs = VERSIONS.get(message_id, [])
    return vs[-1] if vs else None


def count(message_id: str) -> int:
    return len(VERSIONS.get(message_id, []))
