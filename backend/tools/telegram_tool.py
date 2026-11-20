"""
Tool :: Telegram

Lets the agent reach the user anywhere: push progress reports, final
answers, or alerts through the Telegram Bot API while a long task runs.

Setup (once):
1. Create a bot with @BotFather -> get TELEGRAM_BOT_TOKEN
2. Get your chat id (send /start to your bot, then GET
   https://api.telegram.org/bot<TOKEN>/getUpdates -> chat.id)
3. Put both in backend/.env

Uses httpx (async) — no blocking.
"""
from __future__ import annotations

from typing import Any

import httpx

import configs as config
from .base import Tool


class Telegram(Tool):
    name = "Telegram"
    description = (
        "Send a message/report to the user's Telegram chat: "
        "{'message': 'text (markdown supported)'}"
    )
    example = {"message": "Task finished: report.md written to workspace"}

    async def run(self, message: str = "", **_: Any) -> str:
        token, chat_id = config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID
        if not token or not chat_id:
            return (
                "ERROR: Telegram not configured. Add TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID to backend/.env (see tool docstring)."
            )
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message[:4000],
                        "parse_mode": "Markdown",
                    },
                )
                if r.status_code == 200:
                    return "OK: message delivered via Telegram"
                return f"ERROR: Telegram API responded {r.status_code}: {r.text[:300]}"
        except Exception as exc:
            return f"ERROR: Telegram send failed: {exc}"
