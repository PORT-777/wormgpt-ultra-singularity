from typing import Any, Dict, List
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.anthropic.com/v1"
VERSION = "2023-06-01"


@register_plugin
class ClaudePlugin(BasePlugin):
    manifest = PluginManifest(
        id="claude",
        name="Anthropic Claude",
        description="Chat with Claude models via the Anthropic API (claude.ai)",
        long_description=(
            "Direct access to Anthropic's Claude family (Opus, Sonnet, Haiku). "
            "Send prompts or full multi-turn conversations, analyze images, count "
            "tokens before spending them, and enumerate the models your key can use."
        ),
        version="1.0.0",
        author="outcome",
        icon="🟠",
        category="ai",
        tags=["llm", "anthropic", "claude", "chat", "reasoning", "vision"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="claude.chat",
                display_name="Chat",
                description="Send a single prompt to Claude and get the answer text back",
                parameters={
                    "prompt": {"type": "string", "description": "User message"},
                    "model": {"type": "string", "description": "Default claude-sonnet-4-5"},
                    "system": {"type": "string", "description": "System instructions"},
                    "max_tokens": {"type": "integer", "description": "Default 2048"},
                    "temperature": {"type": "number", "description": "0.0 - 1.0"},
                },
            ),
            PluginTool(
                name="claude.chatMessages",
                display_name="Chat (multi-turn)",
                description="Send a full messages array (role/content) to keep conversation context",
                parameters={
                    "messages": {
                        "type": "array",
                        "description": "Array of {role: user|assistant, content: string}",
                    },
                    "model": {"type": "string"},
                    "system": {"type": "string"},
                    "max_tokens": {"type": "integer"},
                },
            ),
            PluginTool(
                name="claude.vision",
                display_name="Analyze Image",
                description="Send an image URL plus a prompt for visual analysis",
                parameters={
                    "prompt": {"type": "string"},
                    "image_url": {"type": "string"},
                    "model": {"type": "string"},
                },
            ),
            PluginTool(
                name="claude.countTokens",
                display_name="Count Tokens",
                description="Count input tokens for a prompt or messages array before sending",
                parameters={
                    "prompt": {"type": "string"},
                    "messages": {"type": "array"},
                    "model": {"type": "string"},
                },
            ),
            PluginTool(
                name="claude.listModels",
                display_name="List Models",
                description="List Claude models available to this API key",
                parameters={},
            ),
        ],
        website_url="https://claude.ai",
        docs_url="https://docs.anthropic.com/en/api/messages",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.credentials["api_key"],
            "anthropic-version": VERSION,
            "content-type": "application/json",
        }

    async def _messages(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{BASE}/messages", headers=self._headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"Anthropic HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()

        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        return {
            "text": text,
            "model": data.get("model"),
            "stop_reason": data.get("stop_reason"),
            "usage": data.get("usage", {}),
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        model = parameters.get("model") or "claude-sonnet-4-5"

        if tool_name == "claude.chat":
            payload: Dict[str, Any] = {
                "model": model,
                "max_tokens": int(parameters.get("max_tokens") or 2048),
                "messages": [{"role": "user", "content": parameters.get("prompt", "")}],
            }
            if parameters.get("system"):
                payload["system"] = parameters["system"]
            if parameters.get("temperature") is not None:
                payload["temperature"] = parameters["temperature"]
            return await self._messages(payload)

        if tool_name == "claude.chatMessages":
            payload = {
                "model": model,
                "max_tokens": int(parameters.get("max_tokens") or 2048),
                "messages": parameters.get("messages") or [],
            }
            if parameters.get("system"):
                payload["system"] = parameters["system"]
            return await self._messages(payload)

        if tool_name == "claude.vision":
            payload = {
                "model": model,
                "max_tokens": 2048,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "url", "url": parameters["image_url"]},
                            },
                            {"type": "text", "text": parameters.get("prompt", "Describe this image")},
                        ],
                    }
                ],
            }
            return await self._messages(payload)

        if tool_name == "claude.countTokens":
            payload = {"model": model}
            if parameters.get("messages"):
                payload["messages"] = parameters["messages"]
            else:
                payload["messages"] = [
                    {"role": "user", "content": parameters.get("prompt", "")}
                ]
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{BASE}/messages/count_tokens", headers=self._headers, json=payload
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Anthropic HTTP {resp.status_code}: {resp.text[:400]}")
                return resp.json()

        if tool_name == "claude.listModels":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/models?limit=100", headers=self._headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Anthropic HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {
                "models": [
                    {"id": m.get("id"), "name": m.get("display_name")}
                    for m in data.get("data", [])
                ]
            }

        raise ValueError(f"Unknown tool: {tool_name}")
