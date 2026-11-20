"""Provider health monitor: status, latency, failure rate, circuit breaker."""
from __future__ import annotations

import time
from typing import Dict, List

HEALTH: Dict[str, dict] = {}


def record(provider: str, ok: bool, latency_ms: int, error: str = "") -> None:
    h = HEALTH.setdefault(provider, {
        "provider": provider, "status": "unknown", "last_success": None,
        "last_error": None, "response_times": [], "failures": 0,
        "successes": 0, "consecutive_failures": 0,
    })
    if ok:
        h["status"] = "healthy"
        h["last_success"] = time.time()
        h["successes"] += 1
        h["consecutive_failures"] = 0
    else:
        h["status"] = "degraded" if h["consecutive_failures"] < 3 else "down"
        h["last_error"] = error
        h["failures"] += 1
        h["consecutive_failures"] += 1
    h["response_times"].append(latency_ms)
    h["response_times"] = h["response_times"][-50:]


def status(provider: str) -> dict:
    return HEALTH.get(provider, {"provider": provider, "status": "unknown"})


def all_status() -> List[dict]:
    out = []
    for p, h in HEALTH.items():
        rts = h.get("response_times", [])
        avg = sum(rts) / len(rts) if rts else 0
        total = h.get("successes", 0) + h.get("failures", 0)
        fr = (h.get("failures", 0) / total) if total else 0.0
        out.append({**h, "avg_response_ms": round(avg, 1),
                    "failure_rate": round(fr, 3)})
    return out


def circuit_open(provider: str) -> bool:
    h = HEALTH.get(provider)
    if not h:
        return False
    return h.get("consecutive_failures", 0) >= 5
