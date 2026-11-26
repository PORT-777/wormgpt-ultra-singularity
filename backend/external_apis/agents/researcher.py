"""Research agent: web-grounded answer via configured search service."""
from __future__ import annotations


async def research(question: str):
    from ..base import ExternalService
    from ..registry import registry
    spec = registry.get("serpapi")
    if spec is None or not spec.available():
        return {"status": "degraded", "reason": "serpapi not configured"}
    try:
        return await ExternalService(spec).getCached("search", {"q": question})
    except Exception as exc:
        return {"status": "degraded", "reason": str(exc)[:300]}
