from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.mistral.ai/v1"


@register_plugin
class MistralPlugin(BasePlugin):
    manifest = PluginManifest(
        id="mistral",
        name="Mistral AI",
        description="Mistral chat, embeddings and fill-in-the-middle coding",
        long_description=(
            "Mistral's open-weight models plus Codestral for code completion. "
            "Includes chat, embeddings, FIM completion and model discovery."
        ),
        version="1.0.0",
        author="outcome",
        icon="🟧",
        category="ai",
        tags=["llm", "mistral", "codestral", "embeddings", "code"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="mistral.chat",
                display_name="Chat",
                description="Send a prompt to a Mistral model",
                parameters={
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "description": "Default mistral-large-latest"},
                    "system": {"type": "string"},
                    "temperature": {"type": "number"},
                },
            ),
            PluginTool(
                name="mistral.chatMessages",
                display_name="Chat (multi-turn)",
                description="Send a full messages array",
                parameters={"messages": {"type": "array"}, "model": {"type": "string"}},
            ),
            PluginTool(
                name="mistral.embed",
                display_name="Embeddings",
                description="Create embeddings for one or more strings",
                parameters={
                    "input": {"type": "string"},
                    "model": {"type": "string", "description": "Default mistral-embed"},
                },
            ),
            PluginTool(
                name="mistral.fim",
                display_name="Code Completion (FIM)",
                description="Fill-in-the-middle code completion for an editor-like workflow",
                parameters={
                    "prompt": {"type": "string", "description": "Code before the cursor"},
                    "suffix": {"type": "string", "description": "Code after the cursor"},
                    "model": {"type": "string", "description": "Default codestral-latest"},
                },
            ),
            PluginTool(
                name="mistral.listModels",
                display_name="List Models",
                description="List models available to this key",
                parameters={},
            ),
        ],
        website_url="https://mistral.ai",
        docs_url="https://docs.mistral.ai/api",
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

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        model = parameters.get("model") or "mistral-large-latest"

        if tool_name in {"mistral.chat", "mistral.chatMessages"}:
            if tool_name == "mistral.chat":
                messages = []
                if parameters.get("system"):
                    messages.append({"role": "system", "content": parameters["system"]})
                messages.append({"role": "user", "content": parameters.get("prompt", "")})
            else:
                messages = parameters.get("messages") or []

            payload: Dict[str, Any] = {"model": model, "messages": messages}
            if parameters.get("temperature") is not None:
                payload["temperature"] = parameters["temperature"]

            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{BASE}/chat/completions", headers=self._headers, json=payload
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Mistral HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            return {
                "text": (choice.get("message") or {}).get("content", ""),
                "model": data.get("model"),
                "usage": data.get("usage", {}),
            }

        if tool_name == "mistral.embed":
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    f"{BASE}/embeddings",
                    headers=self._headers,
                    json={
                        "model": parameters.get("model") or "mistral-embed",
                        "input": [parameters.get("input", "")],
                    },
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Mistral HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            vectors = [item.get("embedding") for item in data.get("data", [])]
            return {
                "model": data.get("model"),
                "dimensions": len(vectors[0]) if vectors and vectors[0] else 0,
                "vectors": vectors,
            }

        if tool_name == "mistral.fim":
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{BASE}/fim/completions",
                    headers=self._headers,
                    json={
                        "model": parameters.get("model") or "codestral-latest",
                        "prompt": parameters.get("prompt", ""),
                        "suffix": parameters.get("suffix", ""),
                    },
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Mistral HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            return {"completion": (choice.get("message") or {}).get("content", "")}

        if tool_name == "mistral.listModels":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/models", headers=self._headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Mistral HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {"models": [m.get("id") for m in data.get("data", [])]}

        raise ValueError(f"Unknown tool: {tool_name}")
