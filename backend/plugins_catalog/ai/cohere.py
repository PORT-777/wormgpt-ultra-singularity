from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.cohere.com"


@register_plugin
class CoherePlugin(BasePlugin):
    manifest = PluginManifest(
        id="cohere",
        name="Cohere",
        description="Command chat, embeddings and reranking for RAG pipelines",
        long_description=(
            "Cohere focuses on enterprise retrieval: Command models for grounded chat, "
            "Embed for vectors and Rerank to reorder search results by relevance."
        ),
        version="1.0.0",
        author="outcome",
        icon="🟣",
        category="ai",
        tags=["llm", "cohere", "embeddings", "rerank", "rag"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="cohere.chat",
                display_name="Chat",
                description="Send a message to a Command model",
                parameters={
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "description": "Default command-a-03-2025"},
                    "preamble": {"type": "string", "description": "System preamble"},
                    "temperature": {"type": "number"},
                },
            ),
            PluginTool(
                name="cohere.embed",
                display_name="Embeddings",
                description="Embed one or more texts",
                parameters={
                    "texts": {"type": "array"},
                    "model": {"type": "string", "description": "Default embed-v4.0"},
                    "input_type": {
                        "type": "string",
                        "description": "search_document | search_query | classification",
                    },
                },
            ),
            PluginTool(
                name="cohere.rerank",
                display_name="Rerank",
                description="Reorder documents by relevance to a query",
                parameters={
                    "query": {"type": "string"},
                    "documents": {"type": "array"},
                    "model": {"type": "string", "description": "Default rerank-v3.5"},
                },
            ),
            PluginTool(
                name="cohere.listModels",
                display_name="List Models",
                description="List Cohere models available to this key",
                parameters={},
            ),
        ],
        website_url="https://cohere.com",
        docs_url="https://docs.cohere.com/reference/about",
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
        if tool_name == "cohere.chat":
            payload: Dict[str, Any] = {
                "model": parameters.get("model") or "command-a-03-2025",
                "messages": [{"role": "user", "content": parameters.get("prompt", "")}],
            }
            if parameters.get("preamble"):
                payload["preamble"] = parameters["preamble"]
            if parameters.get("temperature") is not None:
                payload["temperature"] = parameters["temperature"]

            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(f"{BASE}/v2/chat", headers=self._headers, json=payload)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Cohere HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()

            content = (data.get("message") or {}).get("content") or []
            text = "".join(part.get("text", "") for part in content if part.get("type") == "text")
            return {"text": text, "usage": data.get("usage", {})}

        if tool_name == "cohere.embed":
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{BASE}/v2/embed",
                    headers=self._headers,
                    json={
                        "model": parameters.get("model") or "embed-v4.0",
                        "texts": parameters.get("texts") or [],
                        "input_type": parameters.get("input_type") or "search_document",
                        "embedding_types": ["float"],
                    },
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Cohere HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            vectors = (data.get("embeddings") or {}).get("float") or []
            return {
                "count": len(vectors),
                "dimensions": len(vectors[0]) if vectors else 0,
                "vectors": vectors,
            }

        if tool_name == "cohere.rerank":
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{BASE}/v2/rerank",
                    headers=self._headers,
                    json={
                        "model": parameters.get("model") or "rerank-v3.5",
                        "query": parameters.get("query", ""),
                        "documents": parameters.get("documents") or [],
                    },
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Cohere HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {
                "results": [
                    {"index": r.get("index"), "score": r.get("relevance_score")}
                    for r in data.get("results", [])
                ]
            }

        if tool_name == "cohere.listModels":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{BASE}/v1/models?page_size=100", headers=self._headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Cohere HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
            return {"models": [m.get("name") for m in data.get("models", [])]}

        raise ValueError(f"Unknown tool: {tool_name}")
