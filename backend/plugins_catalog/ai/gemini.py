from typing import Any, Dict, List
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://generativelanguage.googleapis.com/v1beta"


@register_plugin
class GeminiPlugin(BasePlugin):
    manifest = PluginManifest(
        id="gemini",
        name="Google Gemini",
        description="Gemini models, embeddings and vision through Google AI Studio",
        long_description=(
            "Google's Gemini API covers long-context reasoning, image understanding and "
            "text embeddings. This plugin exposes chat, multi-turn, vision, embedding and "
            "model-listing actions using your AI Studio key."
        ),
        version="1.0.0",
        author="outcome",
        icon="🔷",
        category="ai",
        tags=["llm", "google", "gemini", "vision", "embeddings"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="gemini.chat",
                display_name="Chat",
                description="Send a prompt to a Gemini model and return the reply",
                parameters={
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "description": "Default gemini-2.0-flash"},
                    "system": {"type": "string"},
                    "temperature": {"type": "number"},
                },
            ),
            PluginTool(
                name="gemini.chatMessages",
                display_name="Chat (multi-turn)",
                description="Send prior turns as {role: user|model, content: string}[]",
                parameters={
                    "messages": {"type": "array"},
                    "model": {"type": "string"},
                    "system": {"type": "string"},
                },
            ),
            PluginTool(
                name="gemini.vision",
                display_name="Analyze Image",
                description="Analyze an image URL with a text prompt",
                parameters={
                    "prompt": {"type": "string"},
                    "image_url": {"type": "string"},
                    "model": {"type": "string"},
                },
            ),
            PluginTool(
                name="gemini.embed",
                display_name="Embed Text",
                description="Create a text embedding vector",
                parameters={
                    "text": {"type": "string"},
                    "model": {"type": "string", "description": "Default text-embedding-004"},
                },
            ),
            PluginTool(
                name="gemini.listModels",
                display_name="List Models",
                description="List Gemini models and their input token limits",
                parameters={},
            ),
        ],
        website_url="https://aistudio.google.com",
        docs_url="https://ai.google.dev/api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    async def _generate(self, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{BASE}/models/{model}:generateContent?key={self.credentials['api_key']}"
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()

        candidates = data.get("candidates") or [{}]
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        return {
            "text": text,
            "model": data.get("modelVersion"),
            "finish_reason": candidates[0].get("finishReason"),
            "usage": data.get("usageMetadata", {}),
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        model = parameters.get("model") or "gemini-2.0-flash"

        if tool_name == "gemini.chat":
            payload: Dict[str, Any] = {
                "contents": [{"role": "user", "parts": [{"text": parameters.get("prompt", "")}]}]
            }
            if parameters.get("system"):
                payload["systemInstruction"] = {"parts": [{"text": parameters["system"]}]}
            if parameters.get("temperature") is not None:
                payload["generationConfig"] = {"temperature": parameters["temperature"]}
            return await self._generate(model, payload)

        if tool_name == "gemini.chatMessages":
            contents = [
                {
                    "role": "model" if m.get("role") in {"assistant", "model"} else "user",
                    "parts": [{"text": m.get("content", "")}],
                }
                for m in parameters.get("messages") or []
            ]
            payload = {"contents": contents}
            if parameters.get("system"):
                payload["systemInstruction"] = {"parts": [{"text": parameters["system"]}]}
            return await self._generate(model, payload)

        if tool_name == "gemini.vision":
            async with httpx.AsyncClient(timeout=60.0) as client:
                img = await client.get(parameters["image_url"])
                img.raise_for_status()
            import base64

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": img.headers.get("content-type", "image/jpeg"),
                                    "data": base64.b64encode(img.content).decode(),
                                }
                            },
                            {"text": parameters.get("prompt", "Describe this image")},
                        ],
                    }
                ]
            }
            return await self._generate(model, payload)

        if tool_name == "gemini.embed":
            embed_model = parameters.get("model") or "text-embedding-004"
            url = f"{BASE}/models/{embed_model}:embedContent?key={self.credentials['api_key']}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json={"content": {"parts": [{"text": parameters.get("text", "")}]}})
                if resp.status_code >= 400:
                    raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            values = (data.get("embedding") or {}).get("values") or []
            return {"dimensions": len(values), "vector": values}

        if tool_name == "gemini.listModels":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/models?key={self.credentials['api_key']}")
                if resp.status_code >= 400:
                    raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {
                "models": [
                    {
                        "id": m.get("name", "").replace("models/", ""),
                        "display_name": m.get("displayName"),
                        "input_tokens": m.get("inputTokenLimit"),
                    }
                    for m in data.get("models", [])
                ]
            }

        raise ValueError(f"Unknown tool: {tool_name}")
