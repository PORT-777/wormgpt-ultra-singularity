"""Pre-warm frequent queries at startup."""
from __future__ import annotations

from ..cache import cache


FREQUENT = [("openrouter-models", "list", {})]


async def warm():
    from ..base import ExternalService
    from ..registry import registry
    warmed = 0
    for name, action, payload in FREQUENT:
        spec = registry.get(name)
        if spec is None or not spec.available():
            continue
        try:
            value = await ExternalService(spec).query(action, payload)
            cache.set(cache.make_key(name, action, payload), value)
            warmed += 1
        except Exception:
            pass
    return warmed
