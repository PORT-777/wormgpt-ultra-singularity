"""
Provider-agnostic streaming LLM client.

Emits normalized chunks so the rest of the app never touches provider payloads:

    {"type": "text", "content": "..."}
    {"type": "tool_use", "tool_name": "virustotal.lookupHash",
     "parameters": {...}, "id": "call_abc"}
    {"type": "usage", "input_tokens": N, "output_tokens": M}
    {"type": "done"}

Supports:
  * OpenAI-compatible HTTP APIs (OpenAI, DeepSeek, Groq, Together, Ollama, vLLM…)
  * Anthropic Messages API

Configure via environment:
    AI_PROVIDER   openai | anthropic        (default: openai)
    AI_API_KEY    provider secret
    AI_MODEL      model id                  (default: gpt-4o-mini / claude-sonnet-4)
    AI_BASE_URL   override endpoint         (default per provider)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger("AIClient")


DEFAULT_BASE = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
}

DEFAULT_MODEL = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
}

ANTHROPIC_VERSION = "2023-06-01"


class AIProviderError(RuntimeError):
    pass


# ---------------------------------------------------------------- normalization

def _tools_to_openai(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Our tool dicts already follow the OpenAI function schema — pass through."""
    normalized = []
    for tool in tools:
        if "type" in tool and "function" in tool:
            normalized.append(tool)
        else:
            normalized.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
                    },
                }
            )
    return normalized


def _tools_to_anthropic(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for tool in tools:
        fn = tool.get("function", tool)
        out.append(
            {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return out


# ------------------------------------------------------------------ base class

class BaseAIClient:
    provider: str = "base"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("AI_API_KEY", "")
        self.model = model or os.environ.get("AI_MODEL") or DEFAULT_MODEL[self.provider]
        self.base_url = (base_url or os.environ.get("AI_BASE_URL") or DEFAULT_BASE[self.provider]).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        raise NotImplementedError

    async def _with_retries(self, make_request):
        """Retries connection-level failures with exponential backoff."""
        attempt = 0
        while True:
            try:
                return await make_request()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                attempt += 1
                if attempt > self.max_retries:
                    raise AIProviderError(f"provider unreachable after {attempt} attempts: {exc}")
                delay = min(2 ** attempt, 10)
                logger.warning("LLM transport error (%s); retrying in %ss", exc, delay)
                await asyncio.sleep(delay)


# --------------------------------------------------------- OpenAI-compatible

class OpenAIClient(BaseAIClient):
    provider = "openai"

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.api_key:
            raise AIProviderError("AI_API_KEY is not set")

        payload: Dict[str, Any] = {
            "model": self.model,
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [{"role": "system", "content": system}, *messages],
        }
        if tools:
            payload["tools"] = _tools_to_openai(tools)
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Accumulate fragmented tool-call deltas by index
        tool_calls: Dict[int, Dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode(errors="replace")
                    raise AIProviderError(f"HTTP {resp.status_code}: {body[:500]}")

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    if usage := event.get("usage"):
                        yield {
                            "type": "usage",
                            "input_tokens": usage.get("prompt_tokens", 0),
                            "output_tokens": usage.get("completion_tokens", 0),
                        }

                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}

                    if content := delta.get("content"):
                        yield {"type": "text", "content": content}

                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index", 0)
                        slot = tool_calls.setdefault(
                            idx, {"id": None, "name": "", "arguments": ""}
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] += fn["name"]
                        if fn.get("arguments"):
                            slot["arguments"] += fn["arguments"]

                    finish = choices[0].get("finish_reason")
                    if finish == "tool_calls":
                        for slot in tool_calls.values():
                            try:
                                params = json.loads(slot["arguments"] or "{}")
                            except json.JSONDecodeError:
                                params = {"_raw": slot["arguments"]}
                            yield {
                                "type": "tool_use",
                                "id": slot["id"] or slot["name"],
                                "tool_name": slot["name"],
                                "parameters": params,
                            }
                        tool_calls.clear()

        yield {"type": "done"}


# ---------------------------------------------------------------- Anthropic

class AnthropicClient(BaseAIClient):
    provider = "anthropic"

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.api_key:
            raise AIProviderError("AI_API_KEY is not set")

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "stream": True,
            "system": system,
            "messages": messages,
        }
        if tools:
            payload["tools"] = _tools_to_anthropic(tools)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        current_block: Optional[Dict[str, Any]] = None
        tool_input_json = ""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/messages", json=payload, headers=headers
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode(errors="replace")
                    raise AIProviderError(f"HTTP {resp.status_code}: {body[:500]}")

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data:
                        continue
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    etype = event.get("type")

                    if etype == "message_start":
                        usage = (event.get("message") or {}).get("usage") or {}
                        yield {
                            "type": "usage",
                            "input_tokens": usage.get("input_tokens", 0),
                            "output_tokens": 0,
                        }

                    elif etype == "content_block_start":
                        block = event.get("content_block") or {}
                        if block.get("type") == "tool_use":
                            current_block = {"id": block.get("id"), "name": block.get("name")}
                            tool_input_json = ""

                    elif etype == "content_block_delta":
                        delta = event.get("delta") or {}
                        if delta.get("type") == "text_delta":
                            yield {"type": "text", "content": delta.get("text", "")}
                        elif delta.get("type") == "input_json_delta":
                            tool_input_json += delta.get("partial_json", "")

                    elif etype == "content_block_stop":
                        if current_block:
                            try:
                                params = json.loads(tool_input_json or "{}")
                            except json.JSONDecodeError:
                                params = {"_raw": tool_input_json}
                            yield {
                                "type": "tool_use",
                                "id": current_block["id"],
                                "tool_name": current_block["name"],
                                "parameters": params,
                            }
                            current_block = None
                            tool_input_json = ""

                    elif etype == "message_delta":
                        usage = event.get("usage") or {}
                        if usage.get("output_tokens"):
                            yield {
                                "type": "usage",
                                "input_tokens": 0,
                                "output_tokens": usage["output_tokens"],
                            }

                    elif etype == "message_stop":
                        break

        yield {"type": "done"}


# ------------------------------------------------------------------- factory

def build_client() -> BaseAIClient:
    provider = (os.environ.get("AI_PROVIDER") or "openai").lower()
    if provider == "anthropic":
        return AnthropicClient()
    if provider in {"openai", "deepseek", "groq", "together", "ollama", "vllm", "custom"}:
        return OpenAIClient()
    raise AIProviderError(f"Unsupported AI_PROVIDER: {provider}")


# Module-level singleton consumed by the chat router
ai_client: BaseAIClient = build_client()
