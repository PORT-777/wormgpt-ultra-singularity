"""Tool execution log."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

LOGS: List[dict] = []


def record(tool: str, args: dict, result: dict, duration_ms: int,
           session_id: Optional[str] = None, approved: bool = False) -> dict:
    e = {"id": uuid.uuid4().hex[:12], "tool": tool, "args": args,
         "result_ok": bool(result.get("ok")), "result": result,
         "duration_ms": duration_ms, "session_id": session_id,
         "approved": approved, "timestamp": time.time()}
    LOGS.append(e)
    if len(LOGS) > 5000:
        del LOGS[:1000]
    return e


def list_all(limit: int = 100, tool: Optional[str] = None) -> List[dict]:
    out = LOGS
    if tool:
        out = [e for e in out if e["tool"] == tool]
    return list(reversed(out[-limit:]))


def stats() -> dict:
    from collections import Counter
    c = Counter(e["tool"] for e in LOGS)
    ok = sum(1 for e in LOGS if e["result_ok"])
    return {"total": len(LOGS), "success": ok, "failure": len(LOGS) - ok,
            "by_tool": dict(c)}
