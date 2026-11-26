"""Usage and cost monitoring."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UsageEvent:
    model: str
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    ok: bool = True
    cost: float = 0.0
    ts: float = field(default_factory=time.time)


EVENTS: list[UsageEvent] = []


def record(model: str, latency_ms: int, tokens_in: int = 0,
           tokens_out: int = 0, ok: bool = True, cost: float = 0.0) -> None:
    EVENTS.append(UsageEvent(model, latency_ms, tokens_in, tokens_out, ok, cost))


def summary() -> dict[str, Any]:
    by_model: dict[str, int] = defaultdict(int)
    cost_by_model: dict[str, float] = defaultdict(float)
    for e in EVENTS:
        by_model[e.model] += 1
        cost_by_model[e.model] += e.cost
    return {"calls": len(EVENTS),
            "errors": sum(1 for e in EVENTS if not e.ok),
            "total_tokens": sum(e.tokens_in + e.tokens_out for e in EVENTS),
            "total_cost": round(sum(cost_by_model.values()), 6),
            "by_model": dict(by_model),
            "cost_by_model": dict(cost_by_model)}
