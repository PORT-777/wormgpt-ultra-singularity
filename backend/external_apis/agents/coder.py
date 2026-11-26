"""Coder agent wrapper (delegates to orchestrator with coder role)."""
from __future__ import annotations


async def code(task: str):
    from .orchestrator import run
    return await run(task, "coder")
