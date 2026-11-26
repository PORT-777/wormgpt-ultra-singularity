"""Automatic fallback chain for model calls."""
from __future__ import annotations

from ..base import ExternalService
from ..registry import registry


async def call(chain, action, payload):
    last = None
    for name in chain:
        spec = registry.get(name)
        if spec is None or not spec.available():
            continue
        try:
            return await ExternalService(spec).query(action, payload)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"all model candidates failed: {last}")
