"""Async job queue for heavy background tasks."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


class JobQueue:
    def __init__(self):
        self.jobs: dict[str, Any] = {}

    async def submit(self, job_id: str, fn: Callable[[], Awaitable[Any]]):
        self.jobs[job_id] = {"status": "running"}
        try:
            self.jobs[job_id] = {"status": "done", "result": await fn()}
        except Exception as exc:
            self.jobs[job_id] = {"status": "failed", "error": str(exc)[:300]}
        return self.jobs[job_id]

    def status(self, job_id: str):
        return self.jobs.get(job_id, {"status": "unknown"})


queue = JobQueue()
