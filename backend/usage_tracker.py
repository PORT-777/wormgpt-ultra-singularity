"""Token usage + cost tracking (in-memory + SQLite-ready)."""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

RECORDS: List[dict] = []


@dataclass
class UsageRecord:
    timestamp: float
    provider: str
    model: str
    session_id: Optional[str]
    user_id: Optional[str]
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    cost_input: float = 0.0
    cost_output: float = 0.0
    latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cached_tokens

    @property
    def total_cost(self) -> float:
        return self.cost_input + self.cost_output


def record(r: UsageRecord) -> None:
    RECORDS.append(asdict(r))


def summary() -> dict:
    total_in = sum(r["input_tokens"] for r in RECORDS)
    total_out = sum(r["output_tokens"] for r in RECORDS)
    total_cost = sum(r["cost_input"] + r["cost_output"] for r in RECORDS)
    by_model: Dict[str, int] = {}
    for r in RECORDS:
        by_model[r["model"]] = by_model.get(r["model"], 0) + r["input_tokens"] + r["output_tokens"]
    return {
        "requests": len(RECORDS),
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "total_cost": round(total_cost, 6),
        "by_model": by_model,
    }


def recent(limit: int = 50) -> List[dict]:
    return list(reversed(RECORDS[-limit:]))
