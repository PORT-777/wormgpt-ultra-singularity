"""Shared ReAct agent loop."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .tool_registry import call_tool, available, Tool
from .memory import AgentMemory, memory as default_memory


@dataclass
class AgentResult:
    answer: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"


class BaseAgent:
    name: str = "base"
    system_prompt: str = "You are a helpful agent."
    tools: list[str] = []
    max_iterations: int = 10
    memory: AgentMemory = default_memory

    def allowed_tools(self) -> dict[str, Tool]:
        from .tool_registry import TOOLS
        return {n: TOOLS[n] for n in self.tools if n in TOOLS and available(TOOLS[n])}

    async def think(self, task: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        from llm import ask
        tool_desc = ", ".join(self.allowed_tools())
        prompt = (f"{self.system_prompt}\nTask: {task}\nTools: {tool_desc}\n"
                  'Reply JSON: {"thought":"...","tool":"name|none",'
                  '"args":{}, "answer":"..."}')
        try:
            text = await ask(prompt, system="You are a precise JSON-producing planner.")
            m = re.search(r"\{.*\}", text, re.S)
            data = json.loads(m.group(0)) if m else {}
            return {"thought": data.get("thought", ""),
                    "tool": data.get("tool", "none"),
                    "args": data.get("args", {}),
                    "answer": data.get("answer", ""),
                    "is_final": data.get("tool", "none") in ("none", "", None)}
        except Exception as exc:
            return {"answer": f"Model unavailable: {type(exc).__name__}", "is_final": True}

    async def run(self, task: str) -> AgentResult:
        history: list[dict[str, Any]] = []
        for i in range(self.max_iterations):
            thought = await self.think(task, history)
            history.append({"iteration": i + 1, **thought})
            if thought.get("is_final"):
                return AgentResult(answer=thought.get("answer", ""), steps=history)
            observation = await call_tool(thought.get("tool", ""), **thought.get("args", {}))
            history[-1]["observation"] = observation
        return AgentResult(answer="Max iterations reached", steps=history, status="max_iterations")
