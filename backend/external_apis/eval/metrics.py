"""Aggregate metrics from traces."""
from __future__ import annotations

from .tracer import TRACES


def metrics():
    total = len(TRACES)
    latencies = sorted(t["latency_ms"] for t in TRACES)
    return {"calls": total,
            "error_rate": round(sum(1 for t in TRACES if not t["ok"]) / (total or 1), 3),
            "p99_ms": latencies[int(len(latencies) * 0.99)] if latencies else 0}
