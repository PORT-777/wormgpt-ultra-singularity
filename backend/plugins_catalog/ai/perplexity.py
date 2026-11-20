from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.perplexity.ai"


@register_plugin
class PerplexityPlugin(BasePlugin):
    manifest = PluginManifest(
        id="perplexity",
        name="Perplexity",
        description="Search-grounded answers with live citations",
        long_description=(
            "Perplexity's Sonar models browse the web before answering and return the "
            "sources they used. Ideal for current events, vendor research and OSINT."
        ),
        version="1.0.0",
        author="outcome",
        icon="🌀",
        category="ai",
        tags=["llm", "search", "citations", "research", "web"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="perplexity.search",
                display_name="Grounded Search",
                description="Ask a question and get an answer with source citations",
                parameters={
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "description": "Default sonar-pro"},
                    "recency": {"type": "string", "description": "day | week | month | year"},
                },
            ),
            PluginTool(
                name="perplexity.deepResearch",
                display_name="Deep Research",
                description="Long multi-step research report on a topic",
                parameters={"prompt": {"type": "string"}},
            ),
            PluginTool(
                name="perplexity.chatMessages",
                display_name="Chat (multi-turn)",
                description="Send a messages array to a Sonar model",
                parameters={"messages": {"type": "array"}, "model": {"type": "string"}},
            ),
        ],
        website_url="https://www.perplexity.ai",
        docs_url="https://docs.perplexity.ai",
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

    async def _ask(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{BASE}/chat/completions", headers=self._headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"Perplexity HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        return {
            "text": (choice.get("message") or {}).get("content", ""),
            "citations": data.get("citations") or [],
            "model": data.get("model"),
            "usage": data.get("usage", {}),
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "perplexity.search":
            payload: Dict[str, Any] = {
                "model": parameters.get("model") or "sonar-pro",
                "messages": [{"role": "user", "content": parameters.get("prompt", "")}],
            }
            if parameters.get("recency"):
                payload["search_recency_filter"] = parameters["recency"]
            return await self._ask(payload)

        if tool_name == "perplexity.deepResearch":
            return await self._ask(
                {
                    "model": "sonar-deep-research",
                    "messages": [{"role": "user", "content": parameters.get("prompt", "")}],
                }
            )

        if tool_name == "perplexity.chatMessages":
            return await self._ask(
                {
                    "model": parameters.get("model") or "sonar",
                    "messages": parameters.get("messages") or [],
                }
            )

        raise ValueError(f"Unknown tool: {tool_name}")
