"""Route a task to a specialist agent based on keywords."""
from __future__ import annotations

import re

ROLES = ("researcher", "coder", "analyst", "writer")


def choose(task: str) -> str:
    t = str(task or "").lower()
    if re.search(r"code|script|bug|compile|function", t):
        return "coder"
    if re.search(r"data|csv|json|metric|chart", t):
        return "analyst"
    if re.search(r"write|draft|article|report", t):
        return "writer"
    return "researcher"


async def run(task: str, role: str | None = None):
    role = role or choose(task)
    from ..base import ExternalService
    from ..registry import registry
    spec = registry.get("openrouter") or registry.get("huggingface")
    if spec is None or not spec.available():
        return {"role": role, "status": "degraded", "reason": "no model service"}
    try:
        result = await ExternalService(spec).query(
            "route" if spec.name == "openrouter" else "infer",
            {"model": "openai/gpt-4o-mini", "messages": [{"role": "user", "content": task}]})
        return {"role": role, "status": "ok", "result": result}
    except Exception as exc:
        return {"role": role, "status": "degraded", "reason": str(exc)[:300]}
