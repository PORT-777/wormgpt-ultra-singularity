"""OpenAI-compatible provider adapters for Groq/HF/OpenRouter/NVIDIA/Z.AI/Kilo."""
from __future__ import annotations

import os
from typing import Any, AsyncIterator, Dict, List, Optional

from providers import BaseProvider, register_provider
from real_providers import _norm, ProviderError


class OpenAICompatProvider(BaseProvider):
    def __init__(self, name, base_url_env, api_key_env, default_model_env=None):
        self.name = name
        self._base_url_env = base_url_env
        self._api_key_env = api_key_env
        self._default_model_env = default_model_env
        self._client = None

    def _client_(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                base_url=os.getenv(self._base_url_env),
                api_key=os.getenv(self._api_key_env),
            )
        return self._client

    async def chat(self, messages, model, **params):
        try:
            c = self._client_()
            m = model or os.getenv(self._default_model_env or "", "")
            r = await c.chat.completions.create(model=m, messages=messages, **{k: v for k, v in params.items() if v is not None})
            choice = r.choices[0]
            usage = {}
            if r.usage:
                usage = {"input": r.usage.prompt_tokens, "output": r.usage.completion_tokens, "total": r.usage.total_tokens}
            return {"content": choice.message.content or "", "usage": usage}
        except Exception as e:
            raise _norm(e)

    async def stream(self, messages, model, **params):
        try:
            c = self._client_()
            m = model or os.getenv(self._default_model_env or "", "")
            s = await c.chat.completions.create(model=m, messages=messages, stream=True, **{k: v for k, v in params.items() if v is not None})
            async for chunk in s:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield {"type": "token", "data": delta}
            yield {"type": "final", "data": ""}
        except Exception as e:
            yield {"type": "error", "data": str(_norm(e))}

    def supports(self, capability, model):
        return capability in {"text", "streaming"}


# Register (avoid overwriting existing groq if already registered? groq already in real_providers)
# Only register new ones here.
for cfg in [
    ("huggingface", "HF_BASE_URL", "HF_API_KEY", None),
    ("openrouter", "OPENROUTER_BASE_URL", "OPENROUTER_API_KEY", None),
    ("nvidia", "NVIDIA_BUILD_BASE_URL", "NVIDIA_BUILD_API_KEY", None),
    ("zai", "Z_AI_BASE_URL", "Z_AI_API_KEY", None),
    ("kilo", "KILO_BASE_URL", "KILO_API_TOKEN", None),
]:
    p = OpenAICompatProvider(*cfg)
    register_provider(p)
