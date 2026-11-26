"""Tools agents may call, mapped to registered external services."""
from __future__ import annotations

from .. import registry as _reg


def available_tools():
    return [{"name": s.name, "category": s.category, "actions": sorted(s.endpoints)}
            for s in _reg.registry.all() if s.available()]
