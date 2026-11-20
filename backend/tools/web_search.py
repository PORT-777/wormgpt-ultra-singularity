"""
Tool :: WebSearch

DuckDuckGo search via the `ddgs` package (no API key required).
Supports both the new `ddgs` import path and the legacy
`duckduckgo_search` package so either install works.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .base import Tool


class WebSearch(Tool):
    name = "WebSearch"
    description = "Search the public web for current facts, docs, or news."
    example = {"query": "fastapi background tasks best practices"}

    async def run(self, query: str = "", max_results: int = 5, **_: Any) -> str:
        if not query.strip():
            return "ERROR: empty query"

        def _search() -> str:
            try:
                from ddgs import DDGS          # newer package name
            except ImportError:               # pragma: no cover
                from duckduckgo_search import DDGS  # legacy name

            hits = DDGS().text(query, max_results=max_results)
            if not hits:
                return "No results found."
            return "\n\n".join(
                f"[{i + 1}] {h.get('title', '')}\n{h.get('href', h.get('url', ''))}\n"
                f"{(h.get('body') or h.get('snippet') or '')[:400]}"
                for i, h in enumerate(hits)
            )

        # `ddgs` is a blocking requests lib -> push off the event loop
        try:
            return await asyncio.to_thread(_search)
        except Exception as exc:
            return f"ERROR: web search failed: {exc}"
