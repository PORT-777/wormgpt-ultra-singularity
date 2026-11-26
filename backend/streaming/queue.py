"""In-process async job queue for heavy tasks."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


@dataclass
class Job:
    id: str
    task_type: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: Any = None
    error: str = ""


HANDLERS: dict[str, Callable[..., Awaitable[Any]]] = {}


def register_handler(name: str, fn: Callable[..., Awaitable[Any]]) -> None:
    HANDLERS[name] = fn


class JobQueue:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def submit(self, task_type: str, payload: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = Job(job_id, task_type)
        await self.queue.put((job_id, task_type, payload))
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self.worker())
        return job_id

    async def worker(self) -> None:
        while True:
            job_id, task_type, payload = await self.queue.get()
            job = self.jobs[job_id]
            job.status = "running"
            try:
                handler = HANDLERS.get(task_type)
                if handler is None:
                    raise RuntimeError(f"unknown task type: {task_type}")
                job.result = await handler(**payload)
                job.status = "done"
            except Exception as exc:
                job.status = "failed"
                job.error = str(exc)[:300]
            finally:
                self.queue.task_done()

    def status(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return {"status": "unknown"}
        return {"id": job.id, "task_type": job.task_type,
                "status": job.status, "error": job.error}

    def result(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "unknown job"}
        return {"id": job.id, "status": job.status,
                "result": job.result, "error": job.error}


queue = JobQueue()
