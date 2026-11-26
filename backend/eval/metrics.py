"""Platform-wide metrics aggregation from stored traces."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PlatformMetrics(BaseModel):
    total_cost_usd: float = 0.0
    cost_today_usd: float = 0.0
    cost_by_model: dict[str, float] = Field(default_factory=dict)
    cost_by_service: dict[str, float] = Field(default_factory=dict)
    total_requests: int = 0
    requests_today: int = 0
    requests_by_model: dict[str, int] = Field(default_factory=dict)
    cache_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    error_rate: float = 0.0
    avg_faithfulness: float = 0.0
    avg_answer_relevance: float = 0.0
    avg_retrieval_precision: float = 0.0
    total_tokens_used: int = 0
    tokens_today: int = 0
    avg_tokens_per_request: float = 0.0


WINDOWS = {"1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000}


def _load(path: str = "data/traces.jsonl") -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


async def get_metrics(period: str = "24h") -> PlatformMetrics:
    rows = _load()
    window = WINDOWS.get(period, WINDOWS["24h"])
    cutoff = time.time() - window
    recent = [r for r in rows if float(r.get("ts", r.get("timestamp_epoch", 0)) or 0) >= cutoff]
    if recent and "timestamp_epoch" not in recent[0]:
        from datetime import datetime
        def epoch(r):
            try:
                return datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")).timestamp()
            except Exception:
                return 0
        recent = [r for r in recent if epoch(r) >= cutoff]
    total = len(rows) or 1
    lat = sorted(float(r.get("latency_ms", 0)) for r in rows)
    by_model: dict[str, int] = {}
    cost_by_model: dict[str, float] = {}
    for r in rows:
        m = r.get("model", "unknown")
        by_model[m] = by_model.get(m, 0) + 1
        cost_by_model[m] = cost_by_model.get(m, 0.0) + float(r.get("cost_usd", 0))
    tokens = sum(int(r.get("total_tokens", 0)) for r in rows)
    errors = sum(1 for r in rows if not r.get("success", True))
    def pct(q):
        return lat[int(len(lat) * q)] if lat else 0.0
    return PlatformMetrics(
        total_cost_usd=round(sum(cost_by_model.values()), 8),
        cost_today_usd=round(sum(float(r.get("cost_usd", 0)) for r in recent), 8),
        cost_by_model=cost_by_model,
        total_requests=len(rows), requests_today=len(recent),
        requests_by_model=by_model,
        avg_latency_ms=round(sum(lat) / len(lat), 2) if lat else 0.0,
        p50_latency_ms=pct(0.5), p95_latency_ms=pct(0.95), p99_latency_ms=pct(0.99),
        error_rate=round(errors / total, 4),
        total_tokens_used=tokens, tokens_today=sum(int(r.get("total_tokens", 0)) for r in recent),
        avg_tokens_per_request=round(tokens / total, 2))
