"""Content safety agent."""
from __future__ import annotations

from .base_agent import BaseAgent


class ModeratorAgent(BaseAgent):
    name = "moderator"
    system_prompt = "You are a content moderator. Classify and score content safety."
    tools = ["check_toxicity", "classify_text", "rag_query"]
