"""Long-form writing agent."""
from __future__ import annotations

from .base_agent import BaseAgent


class WriterAgent(BaseAgent):
    name = "writer"
    system_prompt = "You are a technical writer. Produce structured, sourced content."
    tools = ["web_search", "rag_query", "summarize_text", "translate_text"]
