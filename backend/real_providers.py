"""Real provider adapters: OpenAI, Gemini, Groq."""
from __future__ import annotations

import os
from typing import Any, AsyncIterator, Dict, List, Optional

from providers import BaseProvider, register_provider


class ProviderError(Exception):
    def __init__(self, kind: str, message: str, status: int = 0):
        super().__init__(message)
        self.kind = kind
        self.status = status


def _norm(err: Exception) -> ProviderError:
    msg = str(err)
    low = msg.lower()
    if "401" in msg or "invalid api key" in low or "unauthorized" in low or "authentication" in low:
        return ProviderError("auth", msg)
    if "429" in msg or "rate limit" in low:
        return ProviderError("rate_limit", msg, 429)
    if "quota" in low or "insufficient" in low:
        return ProviderError("quota", msg)
    if "timeout" in low or "timed out" in low:
        return ProviderError("timeout", msg)
    if "not found" in low or "404" in msg:
        return ProviderError("model_not_found", msg, 404)
    if "network" in low or "connection" in low:
        return ProviderError("network", msg)
    return ProviderError("provider", msg)


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self):
        self._client = None

    def _client_(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._client

    async def chat(self, messages, model, **params):
        try:
            c = self._client_()
            r = await c.chat.completions.create(model=model, messages=messages, **{k: v for k, v in params.items() if v is not None})
            choice = r.choices[0]
            usage = {}
            if r.usage:
                usage = {"input": r.usage.prompt_tokens, "output": r.usage.completion_tokens, "total": r.usage.total_tokens}
            return {"content": choice.message.content or "", "usage": usage, "tool_calls": getattr(choice.message, "tool_calls", None)}
        except Exception as e:
            raise _norm(e)

    async def stream(self, messages, model, **params):
        try:
            c = self._client_()
            s = await c.chat.completions.create(model=model, messages=messages, stream=True, **{k: v for k, v in params.items() if v is not None})
            async for chunk in s:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield {"type": "token", "data": delta}
            yield {"type": "final", "data": ""}
        except Exception as e:
            yield {"type": "error", "data": str(_norm(e))}

    def supports(self, capability, model):
        return capability in {"text", "streaming", "tool_calling", "vision", "structured_output"}


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self):
        self._client = None

    def _client_(self):
        if self._client is None:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com")
        return self._client

    async def chat(self, messages, model, **params):
        try:
            c = self._client_()
            r = await c.chat.completions.create(model=model, messages=messages, **{k: v for k, v in params.items() if v is not None})
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
            s = await c.chat.completions.create(model=model, messages=messages, stream=True, **{k: v for k, v in params.items() if v is not None})
            async for chunk in s:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield {"type": "token", "data": delta}
            yield {"type": "final", "data": ""}
        except Exception as e:
            yield {"type": "error", "data": str(_norm(e))}

    def supports(self, capability, model):
        return capability in {"text", "streaming", "tool_calling"}


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self):
        self._client = None

    def _client_(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        return self._client

    async def chat(self, messages, model, **params):
        try:
            c = self._client_()
            contents = []
            system = None
            for m in messages:
                if m.get("role") == "system":
                    system = m.get("content")
                    continue
                role = "user" if m.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
            cfg = {}
            if system:
                cfg["system_instruction"] = system
            if params.get("temperature") is not None:
                cfg["temperature"] = params["temperature"]
            if params.get("max_tokens") is not None:
                cfg["max_output_tokens"] = params["max_tokens"]
            from google.genai import types
            resp = await c.aio.models.generate_content(model=model, contents=contents, config=types.GenerateContentConfig(**cfg) if cfg else None)
            text = resp.text if hasattr(resp, "text") else ""
            usage = {}
            if getattr(resp, "usage_metadata", None):
                um = resp.usage_metadata
                usage = {"input": getattr(um, "prompt_token_count", 0), "output": getattr(um, "candidates_token_count", 0), "total": getattr(um, "total_token_count", 0)}
            return {"content": text or "", "usage": usage}
        except Exception as e:
            raise _norm(e)

    async def stream(self, messages, model, **params):
        try:
            c = self._client_()
            contents = []
            system = None
            for m in messages:
                if m.get("role") == "system":
                    system = m.get("content")
                    continue
                role = "user" if m.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
            cfg = {}
            if system:
                cfg["system_instruction"] = system
            from google.genai import types
            async for chunk in await c.aio.models.generate_content_stream(model=model, contents=contents, config=types.GenerateContentConfig(**cfg) if cfg else None):
                if chunk.text:
                    yield {"type": "token", "data": chunk.text}
            yield {"type": "final", "data": ""}
        except Exception as e:
            yield {"type": "error", "data": str(_norm(e))}

    def supports(self, capability, model):
        return capability in {"text", "streaming", "vision", "tool_calling"}


register_provider(OpenAIProvider())
register_provider(GroqProvider())
register_provider(GeminiProvider())
