"""Analyst agent wrapper."""
from __future__ import annotations


async def analyze(task: str):
    from .orchestrator import run
    return await run(task, "analyst")
