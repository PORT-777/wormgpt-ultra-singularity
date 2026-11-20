"""Usage limits: per user/model/agent/request/token/cost limits enforced on backend."""
from __future__ import annotations

from typing import Dict, Optional

LIMITS: Dict[str, dict] = {}
USAGE: Dict[str, float] = {}


def set_limit(scope: str, scope_id: str, metric: str, value: float) -> None:
    LIMITS.setdefault(scope, {}).setdefault(scope_id, {})[metric] = value


def get_limit(scope: str, scope_id: str, metric: str) -> Optional[float]:
    return LIMITS.get(scope, {}).get(scope_id, {}).get(metric)


def record_usage(scope: str, scope_id: str, metric: str, amount: float) -> None:
    key = f"{scope}:{scope_id}:{metric}"
    USAGE[key] = USAGE.get(key, 0) + amount


def get_usage(scope: str, scope_id: str, metric: str) -> float:
    return USAGE.get(f"{scope}:{scope_id}:{metric}", 0.0)


def check(scope: str, scope_id: str, metric: str, amount: float = 1.0) -> dict:
    limit = get_limit(scope, scope_id, metric)
    used = get_usage(scope, scope_id, metric)
    if limit is None:
        return {"allowed": True, "limit": None, "used": used}
    allowed = (used + amount) <= limit
    return {"allowed": allowed, "limit": limit, "used": used,
            "remaining": max(0.0, limit - used)}


def list_limits(scope: Optional[str] = None) -> dict:
    if scope:
        return {scope: LIMITS.get(scope, {})}
    return dict(LIMITS)
