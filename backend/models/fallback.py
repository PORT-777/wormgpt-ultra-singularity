"""Fallback chain for model calls."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .registry import MODEL_CATALOG, provider_available

DEFAULT_FALLBACK_CHAIN = [
    "claude-3-5-sonnet", "gpt-4o", "meta-llama/llama-3.1-70b",
    "google/gemini-flash-1.5", "mistralai/mistral-7b",
]


class AllModelsFailedError(RuntimeError):
    pass


@dataclass
class FallbackResult:
    result: Any
    model: str
    note: str = ""


async def call_with_fallback(prompt: str,
                             chain: list[str] | None = None) -> FallbackResult:
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    chain = chain or DEFAULT_FALLBACK_CHAIN
    last = ""
    for model_id in chain:
        spec = MODEL_CATALOG.get(model_id)
        if spec is None or not provider_available(spec.provider):
            last = f"{model_id}: provider unavailable"
            continue
        target = registry.get("anthropic" if spec.provider == "anthropic"
                              else "openai" if spec.provider == "openai"
                              else "openrouter")
        if target is None or not target.available():
            last = f"{model_id}: no service"
            continue
        try:
            result = await asyncio.wait_for(
                ExternalService(target).query(
                    "chat" if target.name == "openai" else
                    "route" if target.name == "openrouter" else "chat",
                    {"model": model_id, "messages": [{"role": "user", "content": prompt}]}),
                timeout=30)
            return FallbackResult(result, model_id)
        except Exception as exc:
            last = f"{model_id}: {type(exc).__name__}: {exc}"
    raise AllModelsFailedError(f"all models failed; last={last[:300]}")
