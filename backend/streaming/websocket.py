"""WebSocket chat handler helper."""
from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .queue import queue


async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            kind = data.get("type", "message")
            if kind == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if kind == "interrupt":
                await websocket.send_json({"type": "interrupted", "session_id": session_id})
                continue
            message = str(data.get("content", ""))
            mode = str(data.get("mode", "chat"))
            if mode == "agent":
                from agents.orchestrator import OrchestratorAgent
                result = await OrchestratorAgent().run(message)
                await websocket.send_json({"type": "step", "content": result.answer,
                                           "agent": result.steps[0].get("routed_to", "orchestrator")
                                           if result.steps else "orchestrator"})
            elif mode == "rag":
                from rag.pipeline import pipeline
                response = await pipeline.query(message)
                await websocket.send_json({"type": "source", "sources":
                                           [s.__dict__ for s in response.sources]})
                await websocket.send_json({"type": "token", "content": response.answer})
            else:
                from .sse import _token_source
                async for token in _token_source(message, "auto"):
                    await websocket.send_json({"type": "token", "content": token})
            await websocket.send_json({"type": "done", "session_id": session_id})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)[:300]})
        except Exception:
            pass
