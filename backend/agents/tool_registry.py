"""Typed tool registry for agents (discover by name, call by name)."""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, str]
    handler: Callable[..., Awaitable[Any]]
    requires: list[str] = field(default_factory=list)

    async def call(self, **kwargs) -> Any:
        return await self.handler(**kwargs)


TOOLS: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    TOOLS[tool.name] = tool
    return tool


def list_tools(available_only: bool = False) -> list[dict[str, Any]]:
    out = []
    for t in TOOLS.values():
        if available_only and not available(t):
            continue
        out.append({"name": t.name, "description": t.description,
                    "parameters": t.parameters, "requires": t.requires})
    return out


def available(tool: Tool) -> bool:
    import os
    return all(os.getenv(k, "").strip() for k in tool.requires)


async def call_tool(name: str, **kwargs) -> Any:
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": f"unknown tool: {name}"}
    if not available(tool):
        return {"error": f"tool {name} disabled: missing {tool.requires}"}
    try:
        return await tool.call(**kwargs)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _wire() -> None:
    from external_apis.base import ExternalService
    from external_apis.registry import registry

    async def _service(name, action, **kw):
        spec = registry.get(name)
        if spec is None or not spec.available():
            return {"error": f"{name} unavailable"}
        return await ExternalService(spec).getCached(action, kw)

    async def rag_query(question: str, top_k: int = 5):
        from rag.pipeline import pipeline
        return await pipeline.query(question, top_k=top_k)

    async def crawl_url(url: str):
        return await _service("crawl4ai", "crawl", url=url)

    async def run_python(code: str):
        from .sandbox import execute_python
        return await execute_python(code)

    async def read_file(path: str):
        from pathlib import Path
        p = Path(path)
        return {"content": p.read_text(encoding="utf-8", errors="replace")} if p.exists() else {"error": "not found"}

    async def write_file(path: str, content: str):
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(p)}

    register(Tool("web_search", "Search the web", {"query": "str", "num_results": "int=5"},
                  lambda query, num_results=5: _service("serpapi", "search", q=query), ["SERPAPI_KEY"]))
    register(Tool("rag_query", "Query internal knowledge base", {"question": "str", "top_k": "int=5"}, rag_query))
    register(Tool("crawl_url", "Fetch and extract a URL", {"url": "str"}, crawl_url))
    register(Tool("run_python", "Execute Python in sandbox", {"code": "str"}, run_python))
    register(Tool("read_file", "Read a workspace file", {"path": "str"}, read_file))
    register(Tool("write_file", "Write a workspace file", {"path": "str", "content": "str"}, write_file))
    for name, action, desc, req in (
        ("github_search", "search", "Search GitHub repositories", ["GITHUB_TOKEN"]),
        ("get_weather", "weather", "Get current weather", ["OPENWEATHER_API_KEY"]),
        ("get_news", "news", "Get news headlines", ["NEWS_API_KEY"]),
        ("compute_math", "query", "Compute with WolframAlpha", ["WOLFRAM_APP_ID"]),
        ("translate_text", "translate", "Translate text", ["NLPCLOUD_API_KEY"]),
        ("classify_text", "classify", "Classify text", ["COHERE_API_KEY"]),
        ("summarize_text", "summarize", "Summarize text", ["SUMMARIZE_AI_API_KEY"]),
        ("check_toxicity", "toxicity", "Score toxicity", ["PERSPECTIVE_API_KEY"]),
        ("transcribe_audio", "assembly", "Transcribe audio", ["ASSEMBLYAI_API_KEY"]),
        ("analyze_image", "classify", "Analyze image", ["CLARIFAI_API_KEY"]),
    ):
        spec_name = {"github_search": "github", "get_weather": "openweathermap",
                     "get_news": "newsapi", "compute_math": "wolfram",
                     "translate_text": "nlpcloud", "classify_text": "cohere",
                     "summarize_text": "summarize-ai", "check_toxicity": "perspective",
                     "transcribe_audio": "assemblyai", "analyze_image": "clarifai"}[name]
        register(Tool(name, desc, {}, lambda a=action, s=spec_name, **kw: _service(s, a, **kw), req))


_wire()
