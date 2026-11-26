"""In-memory model usage/latency monitor."""
from __future__ import annotations

import time
from typing import Any


EVENTS: list[dict[str, Any]] = []


def record(model: str, latency: float, ok: bool):
    EVENTS.append({"model": model, "latency": latency, "ok": ok, "ts": time.time()})


def summary():
    return {"calls": len(EVENTS),
            "errors": sum(1 for e in EVENTS if not e["ok"]),
            "avg_latency": (sum(e["latency"] for e in EVENTS) / len(EVENTS)) if EVENTS else 0}
