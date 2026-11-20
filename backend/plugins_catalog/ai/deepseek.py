from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.deepseek.com"


@register_plugin
class DeepSeekPlugin(BasePlugin):
    manifest = PluginManifest(
        id="deepseek",
        name="DeepSeek",
        description="DeepSeek chat and reasoning models at low cost",
        long_description=(
            "DeepSeek exposes an OpenAI-compatible API with strong coding and math "
            "reasoning models. Includes balance lookup so you can watch spend."
        ),
        version="1.0.0",
        author="outcome",
        icon="🐋",
        category="ai",
        tags=["llm", "deepseek", "reasoning", "coding", "cheap"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="deepseek.chat",
                display_name="Chat",
                description="Send a prompt to deepseek-chat",
                parameters={
                    "prompt": {"type": "string"},
                    "system": {"type": "string"},
                    "temperature": {"type": "number"},
                    "max_tokens": {"type": "integer"},
                },
            ),
            PluginTool(
                name="deepseek.reason",
                display_name="Reason (R1)",
                description="Use the deepseek-reasoner model and return reasoning plus answer",
                parameters={"prompt": {"type": "string"}, "system": {"type": "string"}},
            ),
            PluginTool(
                name="deepseek.chatMessages",
                display_name="Chat (multi-turn)",
                description="Send a full messages array",
                parameters={"messages": {"type": "array"}, "model": {"type": "string"}},
            ),
            PluginTool(
                name="deepseek.balance",
                display_name="Balance",
                description="Check remaining account balance",
                parameters={},
            ),
            PluginTool(
                name="deepseek.listModels",
                display_name="List Models",
                description="List models available to this key",
                parameters={},
            ),
        ],
        website_url="https://platform.deepseek.com",
        docs_url="https://api-docs.deepseek.com",
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
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{BASE}/chat/completions", headers=self._headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return {
            "text": message.get("content", ""),
            "reasoning": message.get("reasoning_content", ""),
            "model": data.get("model"),
            "usage": data.get("usage", {}),
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name in {"deepseek.chat", "deepseek.reason"}:
            messages = []
            if parameters.get("system"):
                messages.append({"role": "system", "content": parameters["system"]})
            messages.append({"role": "user", "content": parameters.get("prompt", "")})
            payload: Dict[str, Any] = {
                "model": "deepseek-reasoner" if tool_name == "deepseek.reason" else "deepseek-chat",
                "messages": messages,
            }
            if parameters.get("temperature") is not None and tool_name == "deepseek.chat":
                payload["temperature"] = parameters["temperature"]
            if parameters.get("max_tokens"):
                payload["max_tokens"] = int(parameters["max_tokens"])
            return await self._chat(payload)

        if tool_name == "deepseek.chatMessages":
            return await self._chat(
                {
                    "model": parameters.get("model") or "deepseek-chat",
                    "messages": parameters.get("messages") or [],
                }
            )

        if tool_name == "deepseek.balance":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/user/balance", headers=self._headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:400]}")
                return resp.json()

        if tool_name == "deepseek.listModels":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/models", headers=self._headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {"models": [m.get("id") for m in data.get("data", [])]}

        raise ValueError(f"Unknown tool: {tool_name}")
