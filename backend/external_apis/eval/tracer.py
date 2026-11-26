"""In-memory trace of model calls."""
from __future__ import annotations

import time
from typing import Any


TRACES: list[dict[str, Any]] = []


def trace(service: str, action: str, start: float, ok: bool):
    TRACES.append({"service": service, "action": action,
                   "latency_ms": round((time.time() - start) * 1000, 1), "ok": ok})
