# core/decision_matrix.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# Logic for complex task branching

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class TaskBranch:
    name: str
    condition: Callable[[dict], bool]
    handler: Callable[[dict], dict]
    priority: int = 0


class DecisionMatrix:
    """Routes tasks to handlers based on evaluated conditions.
    Branches are evaluated in priority order; first match wins."""

    def __init__(self) -> None:
        self._branches: List[TaskBranch] = []

    def register(self, name: str, condition: Callable[[dict], bool],
                 handler: Callable[[dict], dict], priority: int = 0) -> None:
        self._branches.append(TaskBranch(name, condition, handler, priority))
        self._branches.sort(key=lambda b: b.priority, reverse=True)

    def route(self, context: dict) -> Optional[dict]:
        for branch in self._branches:
            try:
                if branch.condition(context):
                    return {
                        "branch": branch.name,
                        "result": branch.handler(context),
                    }
            except Exception:
                continue
        return None

    def branch_count(self) -> int:
        return len(self._branches)
