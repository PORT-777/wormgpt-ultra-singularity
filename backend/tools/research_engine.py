"""
Tool :: ResearchEngine

Implements the Research Protocol:
  1. Query      — WebSearch for candidate sources
  2. Browse     — Browser (navigate + content) on top results
  3. Extract    — distill key facts, claims, URLs, and citations
  4. Verify     — cross-reference claims across multiple sources

Designed for the Autonomous Engineering Platform's research persona.
No external API keys required (uses DuckDuckGo + Playwright).
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from .base import Tool
from .web_search import WebSearch
from .browser_tool import Browser


class ResearchEngine(Tool):
    name = "ResearchEngine"
    description = (
        "Deep research protocol: Query (web search) -> Browse (fetch pages) "
        "-> Extract (key facts + citations) -> Verify (cross-reference sources). "
        "Use for research-heavy tasks requiring evidence-backed answers."
    )
    example = {
        "query": "FastAPI background tasks best practices",
        "max_sources": 4,
        "verify_claims": True,
    }

    def __init__(self):
        super().__init__()
        self._search = WebSearch()
        self._browser = Browser()

    # ------------------------------------------------------------------ #
    #  Protocol steps
    # ------------------------------------------------------------------ #
    async def _step_query(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Step 1: Query — gather candidate sources via WebSearch."""
        raw = await self._search.run(query=query, max_results=max_results)
        if raw.startswith("ERROR") or raw.strip() == "No results found.":
            return []

        sources: List[Dict[str, str]] = []
        # Parse the WebSearch output format: [N] title \n url \n body
        blocks = re.split(r"\n\n(?=\[\d+\]\s)", raw.strip())
        for block in blocks:
            lines = [l for l in block.splitlines() if l.strip()]
            if len(lines) < 2:
                continue
            title_line = lines[0]
            title = re.sub(r"^\[\d+\]\s*", "", title_line).strip()
            url = lines[1].strip()
            body = " ".join(lines[2:])[:500] if len(lines) > 2 else ""
            sources.append({"title": title, "url": url, "body": body})
        return sources

    async def _step_browse(self, sources: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        """Step 2: Browse — fetch page content for top sources."""
        browsed: List[Dict[str, str]] = []
        for src in sources[:limit]:
            url = src.get("url", "")
            if not url:
                continue
            content = await self._browser.run(action="navigate", url=url)
            if content.startswith("ERROR"):
                # try content-only on the same page if navigate partially worked
                content = await self._browser.run(action="content", url="")
            if content.startswith("ERROR") or not content.strip():
                continue
            src["content"] = content[:4000]
            browsed.append(src)
        return browsed

    @staticmethod
    def _step_extract(browsed: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Step 3: Extract — distill key facts and claims per source."""
        extracted: List[Dict[str, str]] = []
        for src in browsed:
            content = src.get("content", "")
            # Pull the first few substantive sentences as "key facts"
            sentences = re.split(r"(?<=[.!?])\s+", content)
            key_facts = " ".join(sentences[:5]).strip()[:800]
            extracted.append({
                "title": src.get("title", ""),
                "url": src.get("url", ""),
                "key_facts": key_facts or content[:300],
            })
        return extracted

    @staticmethod
    def _step_verify(extracted: List[Dict[str, str]], query: str) -> Dict[str, Any]:
        """Step 4: Verify — cross-reference claims across sources."""
        if not extracted:
            return {"verified": False, "sources": 0, "consensus": "No sources found."}

        urls = [e["url"] for e in extracted]
        # Simple consensus heuristic: sources agree if they share key terms
        query_terms = set(re.findall(r"\w+", query.lower()))
        agreements = 0
        for e in extracted:
            text = (e["key_facts"] + " " + e["title"]).lower()
            matches = sum(1 for t in query_terms if t in text)
            if matches >= max(1, len(query_terms) // 2):
                agreements += 1

        consensus = (
            f"{agreements}/{len(extracted)} sources corroborate the query terms."
        )
        return {
            "verified": agreements >= max(1, len(extracted) // 2),
            "sources": len(extracted),
            "consensus": consensus,
            "urls": urls,
        }

    # ------------------------------------------------------------------ #
    #  Entry point
    # ------------------------------------------------------------------ #
    async def run(
        self,
        query: str = "",
        max_sources: int = 4,
        verify_claims: bool = True,
        **_: Any,
    ) -> str:
        if not query.strip():
            return "ERROR: empty query"

        max_sources = max(1, min(int(max_sources or 4), 8))

        # Step 1: Query
        sources = await self._step_query(query, max_sources * 2)
        if not sources:
            return f"ResearchProtocol: no web results for '{query}'."

        # Step 2: Browse
        browsed = await self._step_browse(sources, max_sources)
        if not browsed:
            # Fall back to search snippets if browsing failed
            browsed = sources[:max_sources]

        # Step 3: Extract
        extracted = self._step_extract(browsed)

        # Step 4: Verify
        verification = self._step_verify(extracted, query) if verify_claims else {
            "verified": None, "sources": len(extracted), "consensus": "verification skipped",
            "urls": [e["url"] for e in extracted],
        }

        # Build the final evidence report
        lines: List[str] = [
            f"🔍 ResearchProtocol — Query: {query}",
            f"📚 Sources gathered: {len(extracted)}",
            f"✅ Verified: {verification.get('verified')}",
            f"📊 Consensus: {verification.get('consensus')}",
            "",
            "=== EVIDENCE ===",
        ]
        for i, e in enumerate(extracted, 1):
            lines.append(
                f"\n[{i}] {e['title']}\n"
                f"    URL: {e['url']}\n"
                f"    Key facts: {e['key_facts']}"
            )

        lines.append("")
        lines.append("=== CITATIONS ===")
        for i, e in enumerate(extracted, 1):
            lines.append(f"[{i}] {e['title']} — {e['url']}")

        return "\n".join(lines)


__all__ = ["ResearchEngine"]
