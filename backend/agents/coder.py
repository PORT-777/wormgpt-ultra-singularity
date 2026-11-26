"""Code generation agent."""
from __future__ import annotations

from .base_agent import BaseAgent


class CoderAgent(BaseAgent):
    name = "coder"
    system_prompt = "You are a senior engineer. Write, run and verify code."
    tools = ["run_python", "read_file", "write_file", "github_search", "rag_query"]
