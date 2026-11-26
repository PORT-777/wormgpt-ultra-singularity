"""Server-Sent Events for LLM token streams."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse


async def sse(events: AsyncGenerator[dict[str, Any], None]) -> AsyncGenerator[str, None]:
    async for event in events:
        yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
    yield "data: [DONE]\n\n"


async def _token_source(prompt: str, model: str) -> AsyncGenerator[str, None]:
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("openrouter")
    if spec is None or not spec.available():
        yield "[model unavailable]"
        return
    try:
        result = await ExternalService(spec).query("route", {
            "model": model or "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]})
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        for i in range(0, len(text), 24):
            yield text[i:i + 24]
    except Exception as exc:
        yield f"[error: {type(exc).__name__}]"


async def stream_llm_response(prompt: str, model: str,
                              session_id: str) -> StreamingResponse:
    async def generator():
        yield f"data: {json.dumps({'type': 'session_start', 'session_id': session_id})}\n\n"
        tokens = 0
        async for token in _token_source(prompt, model):
            tokens += len(token.split())
            yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'tokens_used': tokens})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"})
