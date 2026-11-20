"""Live web research: decompose query, search, fetch, aggregate."""
from __future__ import annotations

from typing import List, Dict

from web_tools import search_duckduckgo, fetch


def research(query: str, subqueries: List[str] = None) -> dict:
    qs = subqueries or [query]
    all_results = []
    fetched = []
    for q in qs:
        r = search_duckduckgo(q, limit=5)
        if r.get("ok"):
            for res in r.get("results", []):
                all_results.append({"query": q, **res})
                f = fetch(res["url"])
                if f.get("ok"):
                    fetched.append({"url": res["url"], "title": res["title"],
                                    "text": f["text"][:3000]})
    return {"query": query, "subqueries": qs, "results": all_results,
            "fetched": fetched, "source_count": len(fetched)}


def summarize_sources(fetched: List[dict]) -> str:
    parts = []
    for f in fetched:
        parts.append(f"## {f['title']}\nSource: {f['url']}\n{f['text'][:1500]}")
    return "\n\n".join(parts)
