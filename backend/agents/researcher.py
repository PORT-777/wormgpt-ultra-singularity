"""Web research agent."""
from __future__ import annotations

from .base_agent import BaseAgent


class ResearcherAgent(BaseAgent):
    name = "researcher"
    system_prompt = "You are a senior research analyst. Produce findings with sources."
    tools = ["web_search", "crawl_url", "rag_query", "get_news", "github_search"]
