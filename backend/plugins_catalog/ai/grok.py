from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.x.ai/v1"


@register_plugin
class GrokPlugin(BasePlugin):
    manifest = PluginManifest(
        id="grok",
        name="xAI Grok",
        description="Grok models with optional live search over X posts",
        long_description=(
            "xAI's Grok API with the same OpenAI-compatible surface, plus live search "
            "modes that ground answers in current X/Twitter and web data."
        ),
        version="1.0.0",
        author="outcome",
        icon="⚫",
        category="ai",
        tags=["llm", "xai", "grok", "search", "realtime"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="grok.chat",
                display_name="Chat",
                description="Send a prompt to a Grok model",
                parameters={
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "description": "Default grok-4"},
                    "system": {"type": "string"},
                    "temperature": {"type": "number"},
                },
            ),
            PluginTool(
                name="grok.chatMessages",
                display_name="Chat (multi-turn)",
                description="Send a full messages array to Grok",
                parameters={"messages": {"type": "array"}, "model": {"type": "string"}},
            ),
            PluginTool(
                name="grok.liveSearch",
                display_name="Live Search",
                description="Answer using live search over X posts and the web",
                parameters={
                    "prompt": {"type": "string"},
                    "mode": {"type": "string", "description": "auto | on | off"},
                    "model": {"type": "string"},
                },
            ),
            PluginTool(
                name="grok.listModels",
                display_name="List Models",
                description="List Grok language models available to this key",
                parameters={},
            ),
        ],
        website_url="https://x.ai",
        docs_url="https://docs.x.ai/api",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['api_key']}",
            "Content-Type": "application/json",
        }

    async def _chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{BASE}/chat/completions", headers=self._headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"xAI HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return {
            "text": message.get("content", ""),
            "model": data.get("model"),
            "citations": message.get("citations") or [],
            "usage": data.get("usage", {}),
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        model = parameters.get("model") or "grok-4"

        if tool_name == "grok.chat":
            messages = []
            if parameters.get("system"):
                messages.append({"role": "system", "content": parameters["system"]})
            messages.append({"role": "user", "content": parameters.get("prompt", "")})
            payload: Dict[str, Any] = {"model": model, "messages": messages}
            if parameters.get("temperature") is not None:
                payload["temperature"] = parameters["temperature"]
            return await self._chat(payload)

        if tool_name == "grok.chatMessages":
            return await self._chat(
                {"model": model, "messages": parameters.get("messages") or []}
            )

        if tool_name == "grok.liveSearch":
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": parameters.get("prompt", "")}],
                "search_parameters": {"mode": parameters.get("mode") or "auto"},
            }
            return await self._chat(payload)

        if tool_name == "grok.listModels":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/models", headers=self._headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"xAI HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {"models": [m.get("id") for m in data.get("data", [])]}

        raise ValueError(f"Unknown tool: {tool_name}")
