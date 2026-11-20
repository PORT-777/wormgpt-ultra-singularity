"""Central API request + error logger (no secrets)."""
from __future__ import annotations

import time
from typing import List, Dict, Optional

LOGS: List[dict] = []
ERRORS: List[dict] = []


def log_request(provider: str, model: str, status: int, latency_ms: int,
                retries: int = 0, session_id: Optional[str] = None) -> None:
    LOGS.append({"ts": time.time(), "provider": provider, "model": model,
                 "status": status, "latency_ms": latency_ms, "retries": retries,
                 "session_id": session_id})
    if len(LOGS) > 5000:
        del LOGS[:1000]


def log_error(provider: str, model: str, error_type: str, message: str,
              request_id: Optional[str] = None) -> None:
    ERRORS.append({"ts": time.time(), "provider": provider, "model": model,
                   "type": error_type, "message": message[:500],
                   "request_id": request_id})
    if len(ERRORS) > 2000:
        del ERRORS[:500]


def recent_requests(limit: int = 100, provider: Optional[str] = None) -> List[dict]:
    out = LOGS
    if provider:
        out = [r for r in out if r["provider"] == provider]
    return list(reversed(out[-limit:]))


def recent_errors(limit: int = 100, provider: Optional[str] = None) -> List[dict]:
    out = ERRORS
    if provider:
        out = [e for e in out if e["provider"] == provider]
    return list(reversed(out[-limit:]))
