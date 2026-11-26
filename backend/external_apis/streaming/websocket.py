"""WebSocket handler helper (framework-agnostic receive loop)."""
from __future__ import annotations


async def echo_loop(ws, handler):
    while True:
        message = await ws.receive_text()
        await ws.send_text(str(handler(message)))
