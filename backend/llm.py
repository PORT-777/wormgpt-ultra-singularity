"""Shared LLM call helper using the configured working route.

OpenRouter's configured key returns HTTP 401 in this environment, so internal
capabilities that need generation go through the Groq route. A single helper
keeps that decision in one place.
"""
from __future__ import annotations

from typing import Optional

DEFAULT_MODEL = "openai/gpt-oss-120b"
_GROQ_MODELS = {
    "openai/gpt-oss-120b", "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b", "allam-2-7b",
}


async def ask(prompt: str, system: str = "You are a concise, accurate assistant.",
              model: Optional[str] = None, timeout: float = 90.0) -> str:
    import asyncio
    from langchain_core.messages import HumanMessage, SystemMessage
    from model_router import ROUTER

    target = model if model in _GROQ_MODELS else DEFAULT_MODEL
    _, brain = ROUTER.resolve("groq", task=str(prompt)[:200])
    if brain is None:
        raise RuntimeError("no Groq brain available")
    reply = await asyncio.wait_for(brain.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=str(prompt)),
    ]), timeout=timeout)
    content = getattr(reply, "content", "")
    return content if isinstance(content, str) else str(content or "")
