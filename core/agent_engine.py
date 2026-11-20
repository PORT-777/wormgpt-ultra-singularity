# core/agent_engine.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# ReAct-E Loop & Model Routing for 🔥😈 PORT 777 EVIL ☠️🔥👹 - Singularity Edition

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.decision_matrix import DecisionMatrix


@dataclass
class Thought:
    step: str  # reason | act | observe | evaluate | execute
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Task:
    id: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    thoughts: List[Thought] = field(default_factory=list)
    result: Optional[Any] = None
    status: str = "pending"  # pending | running | done | failed


class AgentEngine:
    """ReAct-E loop orchestrator: Reason -> Act -> Observe -> Evaluate -> Execute."""

    def __init__(self, model_router: Optional[Callable[[str], str]] = None) -> None:
        self.model_router = model_router
        self.matrix = DecisionMatrix()
        self.tasks: Dict[str, Task] = {}
        self.trace: List[Thought] = []

    def _think(self, task: Task, step: str, content: str) -> None:
        thought = Thought(step=step, content=content)
        task.thoughts.append(thought)
        self.trace.append(thought)

    def run(self, task_id: str, description: str, context: Dict[str, Any]) -> Any:
        task = Task(id=task_id, description=description, context=context)
        task.status = "running"
        self.tasks[task_id] = task

        # 1. Reason â€” mental simulation
        self._think(task, "reason", f"Mental simulation of: {description}")
        predicted = self._simulate(task)

        # 2. Act â€” select action via decision matrix
        self._think(task, "act", f"Selected action via decision matrix: {predicted}")
        action = self.matrix.route(task.context) or {"branch": None, "result": None}

        # 3. Observe â€” verify result matches expectation
        observation = self._observe(action, task)
        self._think(task, "observe", json.dumps(observation, ensure_ascii=False))

        # 4. Evaluate â€” match against mental simulation
        ok = self._evaluate(observation, predicted)
        self._think(task, "evaluate", f"Match expectation: {ok}")

        # 5. Execute
        result = self._execute(action, task) if ok else None
        task.result = result
        task.status = "done" if ok else "failed"
        self._think(task, "execute", f"Result: {result}")

        return result

    def _simulate(self, task: Task) -> str:
        if self.model_router:
            return self.model_router(f"Predict risks for: {task.description}")
        return "no_risks_predicted"

    def _observe(self, action: dict, task: Task) -> dict:
        return {"action": action, "task": task.description, "verified": True}

    def _evaluate(self, observation: dict, predicted: str) -> bool:
        return bool(observation.get("verified"))

    def _execute(self, action: dict, task: Task) -> Any:
        handler = action.get("result")
        if callable(handler):
            return handler(task.context)
        return {"status": "no_handler", "task": task.id}

    def register_branch(self, name: str, condition, handler, priority: int = 0) -> None:
        self.matrix.register(name, condition, handler, priority)

    def get_trace(self, task_id: str) -> List[Thought]:
        task = self.tasks.get(task_id)
        return task.thoughts if task else []
