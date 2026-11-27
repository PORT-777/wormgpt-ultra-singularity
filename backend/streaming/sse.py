"""Server-Sent Events for LLM token streams."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse

# Models known to work on the configured Groq route. OpenRouter's configured
# key currently returns HTTP 401, so Groq is the default chat transport.
_GROQ_MODELS = {
    "openai/gpt-oss-120b", "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b", "allam-2-7b",
}
_DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


async def sse(events: AsyncGenerator[dict[str, Any], None]) -> AsyncGenerator[str, None]:
    async for event in events:
        yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
    yield "data: [DONE]\n\n"


async def _token_source(prompt: str, model: str = "") -> AsyncGenerator[str, None]:
    from langchain_core.messages import HumanMessage, SystemMessage
    from model_router import ROUTER

    target = model if model in _GROQ_MODELS else _DEFAULT_GROQ_MODEL
    try:
        _, brain = ROUTER.resolve("groq", task=str(prompt)[:200])
        if brain is None:
            yield "[model unavailable: groq]"
            return
        reply = await brain.ainvoke([
            SystemMessage(content="You are a concise, accurate assistant."),
            HumanMessage(content=str(prompt)),
        ])
        text = getattr(reply, "content", "")
        text = text if isinstance(text, str) else str(text or "")
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
