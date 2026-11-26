"""Daily health check across every registered integration."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .base import ExternalService
from .registry import registry


async def check_all() -> List[Dict[str, Any]]:
    async def one(spec):
        try:
            return await ExternalService(spec).healthCheck()
        except Exception as exc:
            return {"status": "degraded", "service": spec.name,
                    "reason": f"{type(exc).__name__}: {exc}"[:200]}
    return list(await asyncio.gather(*(one(s) for s in registry.all())))


async def health_dashboard() -> Dict[str, Any]:
    results = await check_all()
    ok = sum(1 for r in results if r["status"] == "ok")
    return {
        "status": "ok" if ok == len(results) else "degraded",
        "total": len(results), "ok": ok,
        "services": results,
    }
