from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.openai.com/v1"


@register_plugin
class OpenAIPlugin(BasePlugin):
    manifest = PluginManifest(
        id="openai",
        name="OpenAI",
        description="GPT models, embeddings, images and moderation via the OpenAI API",
        long_description=(
            "Use OpenAI's platform directly: chat with GPT models, generate embeddings "
            "for retrieval, create images, classify content with the moderation endpoint, "
            "and list every model your key can reach."
        ),
        version="1.0.0",
        author="outcome",
        icon="🟢",
        category="ai",
        tags=["llm", "openai", "gpt", "embeddings", "images"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="openai.chat",
                display_name="Chat",
                description="Send a prompt to a GPT model and return the reply text",
                parameters={
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "description": "Default gpt-4o-mini"},
                    "system": {"type": "string"},
                    "temperature": {"type": "number"},
                    "max_tokens": {"type": "integer"},
                },
            ),
            PluginTool(
                name="openai.chatMessages",
                display_name="Chat (multi-turn)",
                description="Send a full messages array to keep conversation context",
                parameters={
                    "messages": {"type": "array"},
                    "model": {"type": "string"},
                    "temperature": {"type": "number"},
                },
            ),
            PluginTool(
                name="openai.embeddings",
                display_name="Embeddings",
                description="Create vector embeddings for text (single string or array)",
                parameters={
                    "input": {"type": "string"},
                    "model": {"type": "string", "description": "Default text-embedding-3-small"},
                },
            ),
            PluginTool(
                name="openai.generateImage",
                display_name="Generate Image",
                description="Generate an image from a prompt and return its URL",
                parameters={
                    "prompt": {"type": "string"},
                    "size": {"type": "string", "description": "1024x1024 | 1024x1792 | 1792x1024"},
                    "model": {"type": "string", "description": "Default gpt-image-1"},
                },
            ),
            PluginTool(
                name="openai.moderate",
                display_name="Moderate Text",
                description="Check text against OpenAI's safety categories",
                parameters={"input": {"type": "string"}},
            ),
            PluginTool(
                name="openai.listModels",
                display_name="List Models",
                description="List every model available to this API key",
                parameters={},
            ),
        ],
        website_url="https://platform.openai.com",
        docs_url="https://platform.openai.com/docs/api-reference",
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

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{BASE}{path}", headers=self._headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"OpenAI HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "openai.chat":
            messages = []
            if parameters.get("system"):
                messages.append({"role": "system", "content": parameters["system"]})
            messages.append({"role": "user", "content": parameters.get("prompt", "")})
            payload: Dict[str, Any] = {
                "model": parameters.get("model") or "gpt-4o-mini",
                "messages": messages,
            }
            if parameters.get("temperature") is not None:
                payload["temperature"] = parameters["temperature"]
            if parameters.get("max_tokens"):
                payload["max_tokens"] = int(parameters["max_tokens"])
            data = await self._post("/chat/completions", payload)
            choice = (data.get("choices") or [{}])[0]
            return {
                "text": (choice.get("message") or {}).get("content", ""),
                "model": data.get("model"),
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage", {}),
            }

        if tool_name == "openai.chatMessages":
            payload = {
                "model": parameters.get("model") or "gpt-4o-mini",
                "messages": parameters.get("messages") or [],
            }
            if parameters.get("temperature") is not None:
                payload["temperature"] = parameters["temperature"]
            data = await self._post("/chat/completions", payload)
            choice = (data.get("choices") or [{}])[0]
            return {
                "text": (choice.get("message") or {}).get("content", ""),
                "model": data.get("model"),
                "usage": data.get("usage", {}),
            }

        if tool_name == "openai.embeddings":
            data = await self._post(
                "/embeddings",
                {
                    "model": parameters.get("model") or "text-embedding-3-small",
                    "input": parameters.get("input", ""),
                },
            )
            vectors = [item.get("embedding") for item in data.get("data", [])]
            return {
                "model": data.get("model"),
                "dimensions": len(vectors[0]) if vectors and vectors[0] else 0,
                "vectors": vectors,
            }

        if tool_name == "openai.generateImage":
            data = await self._post(
                "/images/generations",
                {
                    "model": parameters.get("model") or "gpt-image-1",
                    "prompt": parameters.get("prompt", ""),
                    "size": parameters.get("size") or "1024x1024",
                    "n": 1,
                },
            )
            items = data.get("data", [])
            return {"images": [{"url": i.get("url"), "b64": bool(i.get("b64_json"))} for i in items]}

        if tool_name == "openai.moderate":
            data = await self._post(
                "/moderations",
                {
                    "model": "omni-moderation-latest",
                    "input": parameters.get("input", ""),
                },
            )
            result = (data.get("results") or [{}])[0]
            flagged = [k for k, v in (result.get("categories") or {}).items() if v]
            return {"flagged": result.get("flagged", False), "categories": flagged}

        if tool_name == "openai.listModels":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/models", headers=self._headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"OpenAI HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {"models": sorted(m.get("id", "") for m in data.get("data", []))}

        raise ValueError(f"Unknown tool: {tool_name}")
