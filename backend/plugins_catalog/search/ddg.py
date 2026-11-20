from typing import Any, Dict, List
import httpx
import re
import html as html_lib

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://html.duckduckgo.com/html/"


@register_plugin
class DDGSearchPlugin(BasePlugin):
    manifest = PluginManifest(
        id="ddgsearch",
        name="DuckDuckGo Search",
        description="Keyless web search with instant answers and result URLs",
        long_description=(
            "DuckDuckGo's HTML search endpoint: run queries, get instant-answer "
            "snippets (when available), and return a ranked list of result URLs "
            "and titles. No API key needed."
        ),
        version="1.0.0",
        author="outcome",
        icon="🔍",
        category="search",
        tags=["search", "web", "research", "osint", "keyless"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="ddgsearch.search",
                display_name="Web Search",
                description="Search the web and return titles, snippets and URLs",
                parameters={
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "description": "Default 10, max 25"},
                    "region": {"type": "string", "description": "wt-us | wt-wt | ar-ae"},
                },
            ),
            PluginTool(
                name="ddgsearch.instant",
                display_name="Instant Answer",
                description="Get the instant-answer box (topic, abstract, related) for a query",
                parameters={"query": {"type": "string"}},
            ),
        ],
        website_url="https://duckduckgo.com",
        docs_url="https://duckduckgo.com",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        query = parameters.get("query", "")
        max_results = min(int(parameters.get("max_results") or 10), 25)
        region = parameters.get("region") or "wt-wt"

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.post(
                BASE,
                data={"q": query, "kl": region, "kp": "-2"},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
                    "Accept": "text/html",
                },
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"DDG HTTP {resp.status_code}: {resp.text[:300]}")
            html_text = resp.text

        results: List[Dict[str, str]] = []
        for block in re.findall(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            html_text,
            re.I | re.S,
        ):
            url = html_lib.unescape(block[0])
            title = re.sub(r"<[^>]+>", " ", block[1])
            title = html_lib.unescape(re.sub(r"\s+", " ", title)).strip()
            results.append({"url": url, "title": title})

        snippets: List[Dict[str, str]] = []
        for block in re.findall(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html_text, re.I | re.S
        ):
            snippets.append(
                {"text": html_lib.unescape(re.sub(r"<[^>]+>", " ", block)).strip()}
            )

        out = []
        for i, r in enumerate(results[:max_results]):
            snippet = snippets[i]["text"] if i < len(snippets) else ""
            out.append({"title": r["title"], "url": r["url"], "snippet": snippet})

        if tool_name == "ddgsearch.instant":
            abstract = ""
            for block in re.findall(
                r'<div[^>]+class="result__body"[^>]*>(.*?)</div>', html_text, re.I | re.S
            ):
                abstract = html_lib.unescape(re.sub(r"<[^>]+>", " ", block)).strip()
                break
            return {"query": query, "abstract": abstract, "results": out}

        return {"query": query, "count": len(out), "results": out}