"""Writer agent wrapper."""
from __future__ import annotations


async def write(task: str):
    from .orchestrator import run
    return await run(task, "writer")
