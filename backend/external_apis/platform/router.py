"""Intelligent request router across internal services."""
from __future__ import annotations

from ..base import ExternalService
from ..registry import registry


async def dispatch(service: str, action: str, payload: dict):
    spec = registry.get(service)
    if spec is None:
        return {"available": False, "reason": "unknown service"}
    return await ExternalService(spec).getCached(action, payload)
