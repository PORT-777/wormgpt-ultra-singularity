"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Background Task Scheduler

Runs scheduled agent prompts on an interval â€” "agent cron".
Example: schedule  "Ø§Ø¨Ø­Ø« Ø¹Ù† Ø³Ø¹Ø± Ø§Ù„Ø°Ù‡Ø¨ ÙˆØ§Ø±Ø³Ù„ ØªÙ‚Ø±ÙŠØ± telegram"
with interval 60 min â†’ the platform wakes up hourly, runs the full
agent pipeline (memoryâ†’planâ†’loopâ†’reflect), and pushes the result to
Telegram if configured.

Uses the same AgentEngine instance (via asyncio.create_task on the
FastAPI event loop); started from main.py's lifespan. Tasks live in
SQLite (storage.scheduled_tasks).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

import configs as config
import storage
from agent_engine import ENGINE

log = logging.getLogger("scheduler")

CHECK_INTERVAL = 20          # seconds between due-check sweeps
MAX_PARALLEL = 1             # run scheduled tasks strictly one at a time


class TaskScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._semaphore = asyncio.Semaphore(MAX_PARALLEL)

    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_forever(),
                                             name="🔥😈 PORT 777 EVIL ☠️🔥👹-scheduler")
            log.info("scheduler started")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    # ------------------------------------------------------------------ #
    async def _run_forever(self) -> None:
        while True:
            try:
                tasks = storage.due_tasks()
                for t in tasks:
                    await self._execute(t)
            except asyncio.CancelledError:
                return
            except Exception as exc:        # scheduler must never die
                log.exception("scheduler sweep failed: %s", exc)
            await asyncio.sleep(CHECK_INTERVAL)

    # ------------------------------------------------------------------ #
    async def _execute(self, task: Dict) -> None:
        async with self._semaphore:
            log.info("running scheduled task #%s", task["id"])
            final = ""
            try:
                async for ev in ENGINE.run_stream(task["prompt"],
                                                  history=[],
                                                  model_route="auto"):
                    if ev.get("type") == "final":
                        final = ev.get("data", "")
            except Exception as exc:
                final = f"scheduled task crashed: {exc}"
            storage.complete_task(int(task["id"]), final)

            if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
                await self._push_telegram(task["prompt"], final)

    # ------------------------------------------------------------------ #
    async def _push_telegram(self, prompt: str, result: str) -> None:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    f"https://api.telegram.org"
                    f"/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": config.TELEGRAM_CHAT_ID,
                          "text": f"â° Scheduled task report\n\n"
                                  f"Prompt: {prompt[:300]}\n\n"
                                  f"{result[:3500]}"})
        except Exception as exc:
            log.warning("telegram push failed: %s", exc)


SCHEDULER = TaskScheduler()
