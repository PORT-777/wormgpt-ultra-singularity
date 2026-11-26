"""Data analysis agent."""
from __future__ import annotations

from .base_agent import BaseAgent


class AnalystAgent(BaseAgent):
    name = "analyst"
    system_prompt = "You are a data analyst. Analyze data and report insights."
    tools = ["run_python", "read_file", "compute_math", "rag_query"]
