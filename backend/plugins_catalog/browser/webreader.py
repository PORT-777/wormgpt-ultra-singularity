"""Keyless web reader: turns any URL into clean text, links and metadata."""

import asyncio
import html as html_lib
import re
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _clean_html(raw: str) -> Dict[str, Any]:
    title = ""
    match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    if match:
        title = html_lib.unescape(re.sub(r"\s+", " ", match.group(1))).strip()

    description = ""
    desc = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
        raw,
        re.I,
    )
    if desc:
        description = html_lib.unescape(desc.group(1)).strip()

    body = re.sub(r"<(script|style|noscript|svg|iframe)[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", body)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return {"title": title, "description": description, "text": text.strip()}


def _links(raw: str, base: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    seen = set()
    for href, label in re.findall(
        r'<a[^>]+href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', raw, re.I | re.S
    ):
        url = urljoin(base, html_lib.unescape(href))
        if url in seen or url.startswith("javascript:"):
            continue
        seen.add(url)
        text = re.sub(r"<[^>]+>", " ", label)
        out.append({"url": url, "text": html_lib.unescape(re.sub(r"\s+", " ", text)).strip()})
    return out


@register_plugin
class WebReaderPlugin(BasePlugin):
    manifest = PluginManifest(
        id="webreader",
        name="Web Reader",
        description="Read any page as clean text, extract links and parse sitemaps",
        long_description=(
            "A built-in, keyless browsing layer: fetch a page and get readable text "
            "with title and description, pull every outbound link, read several URLs "
            "at once, and expand a sitemap into a crawl plan. Works even when no "
            "browser automation service is configured."
        ),
        version="1.0.0",
        author="outcome",
        icon="🌐",
        category="browser",
        tags=["browser", "web", "reader", "scraping", "research"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="webreader.read",
                display_name="Read Page",
                description="Fetch a URL and return title, description and clean text",
                parameters={
                    "url": {"type": "string"},
                    "max_chars": {"type": "integer", "description": "Default 20000"},
                },
            ),
            PluginTool(
                name="webreader.readMany",
                display_name="Read Many",
                description="Fetch up to 8 URLs in parallel and return their text",
                parameters={
                    "urls": {"type": "array"},
                    "max_chars": {"type": "integer", "description": "Per page, default 6000"},
                },
            ),
            PluginTool(
                name="webreader.links",
                display_name="Extract Links",
                description="List every link on a page resolved against the base URL",
                parameters={"url": {"type": "string"}, "limit": {"type": "integer"}},
            ),
            PluginTool(
                name="webreader.sitemap",
                display_name="Sitemap",
                description="Read a sitemap.xml (including sitemap indexes) and list URLs",
                parameters={"url": {"type": "string"}, "limit": {"type": "integer"}},
            ),
            PluginTool(
                name="webreader.head",
                display_name="Check URL",
                description="Return status, content type, size and final URL without the body",
                parameters={"url": {"type": "string"}},
            ),
        ],
        website_url="https://developer.mozilla.org/docs/Web/HTTP",
        docs_url="https://developer.mozilla.org/docs/Web/HTTP",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    @staticmethod
    def _client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=45.0,
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "en,ar;q=0.8"},
        )

    async def _fetch(self, client: httpx.AsyncClient, url: str) -> str:
        if not urlparse(url).scheme:
            url = "https://" + url
        resp = await client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"fetch {url} -> HTTP {resp.status_code}")
        return resp.text

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with self._client() as client:
            if tool_name == "webreader.read":
                raw = await self._fetch(client, parameters["url"])
                data = _clean_html(raw)
                limit = int(parameters.get("max_chars") or 20000)
                return {
                    "url": parameters["url"],
                    "title": data["title"],
                    "description": data["description"],
                    "chars": len(data["text"]),
                    "text": data["text"][:limit],
                }

            if tool_name == "webreader.readMany":
                urls = (parameters.get("urls") or [])[:8]
                limit = int(parameters.get("max_chars") or 6000)

                async def one(u: str) -> Dict[str, Any]:
                    try:
                        raw = await self._fetch(client, u)
                        d = _clean_html(raw)
                        return {"url": u, "title": d["title"], "text": d["text"][:limit]}
                    except Exception as exc:
                        return {"url": u, "error": str(exc)}

                return {"pages": await asyncio.gather(*(one(u) for u in urls))}

            if tool_name == "webreader.links":
                raw = await self._fetch(client, parameters["url"])
                links = _links(raw, parameters["url"])
                return {
                    "count": len(links),
                    "links": links[: int(parameters.get("limit") or 200)],
                }

            if tool_name == "webreader.sitemap":
                raw = await self._fetch(client, parameters["url"])
                locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", raw, re.I | re.S)
                return {
                    "is_index": "<sitemapindex" in raw.lower(),
                    "count": len(locs),
                    "urls": locs[: int(parameters.get("limit") or 500)],
                }

            if tool_name == "webreader.head":
                url = parameters["url"]
                if not urlparse(url).scheme:
                    url = "https://" + url
                resp = await client.head(url)
                if resp.status_code >= 400:
                    resp = await client.get(url, headers={"Range": "bytes=0-0"})
                return {
                    "url": str(resp.url),
                    "status": resp.status_code,
                    "content_type": resp.headers.get("content-type"),
                    "content_length": resp.headers.get("content-length"),
                    "server": resp.headers.get("server"),
                }

            raise ValueError(f"Unknown tool: {tool_name}")
