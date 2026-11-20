"""Human approval system for sensitive operations."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

try:
    import configs as config

    ZERO_REFUSAL = bool(getattr(config, "ZERO_REFUSAL", False))
except Exception:
    ZERO_REFUSAL = False

APPROVALS: Dict[str, dict] = {}


SENSITIVE_OPS = {"delete_file", "write_file", "execute_command", "publish",
                  "send_external", "change_settings", "delete_data"}


def request(op: str, details: dict, requester: str = "agent") -> dict:
    aid = uuid.uuid4().hex[:12]
    a = {"id": aid, "operation": op, "details": details, "requester": requester,
         "status": "approved" if ZERO_REFUSAL else "pending",
         "created_at": time.time(), "decided_at": time.time() if ZERO_REFUSAL else None,
         "decided_by": "zero_refusal" if ZERO_REFUSAL else None}
    APPROVALS[aid] = a
    return a


def approve(aid: str, by: str = "user") -> Optional[dict]:
    a = APPROVALS.get(aid)
    if not a:
        return None
    if a["status"] == "approved":
        return a
    if a["status"] != "pending":
        return None
    a["status"] = "approved"
    a["decided_at"] = time.time()
    a["decided_by"] = by
    return a


def reject(aid: str, by: str = "user") -> Optional[dict]:
    a = APPROVALS.get(aid)
    if not a or a["status"] != "pending":
        return None
    a["status"] = "rejected"
    a["decided_at"] = time.time()
    a["decided_by"] = by
    return a


def get(aid: str) -> Optional[dict]:
    return APPROVALS.get(aid)


def list_pending() -> List[dict]:
    return [a for a in APPROVALS.values() if a["status"] == "pending"]


def list_all() -> List[dict]:
    return list(APPROVALS.values())


def is_sensitive(op: str) -> bool:
    return op in SENSITIVE_OPS
