"""Meta-agent routing tasks to specialists."""
from __future__ import annotations

import re
from typing import Any

from .base_agent import AgentResult, BaseAgent
from .analyst import AnalystAgent
from .coder import CoderAgent
from .moderator import ModeratorAgent
from .researcher import ResearcherAgent
from .writer import WriterAgent


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"
    system_prompt = "You route tasks to the best specialist agent."
    sub_agents = {
        "research": ResearcherAgent,
        "code": CoderAgent,
        "analysis": AnalystAgent,
        "writing": WriterAgent,
        "moderation": ModeratorAgent,
    }

    async def classify_task(self, task: str) -> str:
        t = str(task or "").lower()
        if re.search(r"code|script|bug|function|compile|python", t):
            return "code"
        if re.search(r"data|csv|json|metric|analy", t):
            return "analysis"
        if re.search(r"write|article|report|draft|summari", t):
            return "writing"
        if re.search(r"toxic|safe|moderat|classif", t):
            return "moderation"
        return "research"

    async def route(self, task: str) -> str:
        return await self.classify_task(task)

    async def run(self, task: str) -> AgentResult:
        name = await self.route(task)
        agent = self.sub_agents[name]()
        result = await agent.run(task)
        result.steps.insert(0, {"routed_to": name})
        return result
