"""Smart model router with task detection and explainable selection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .registry import MODEL_CATALOG, ModelSpec, provider_available


class RoutingStrategy(str, Enum):
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    BEST_QUALITY = "best_quality"
    BALANCED = "balanced"
    TASK_OPTIMAL = "task_optimal"


@dataclass(frozen=True)
class SelectedModel:
    name: str
    spec: ModelSpec
    reason: str
    strategy: RoutingStrategy


def detect_task(prompt: str) -> str:
    t = str(prompt or "").lower()
    if re.search(r"code|script|function|debug|compile", t):
        return "code"
    if re.search(r"translat|multilingual|arabic|spanish", t):
        return "multilingual"
    if re.search(r"image|vision|screenshot|picture", t):
        return "vision"
    if len(t) > 20000:
        return "long-context"
    return "general"


async def route_request(prompt: str, task_type: str | None = None,
                        strategy: RoutingStrategy = RoutingStrategy.TASK_OPTIMAL,
                        max_cost_per_1k: float | None = None,
                        required_context: int | None = None,
                        available_providers: list[str] | None = None) -> SelectedModel:
    task = task_type or detect_task(prompt)
    candidates = []
    for name, spec in MODEL_CATALOG.items():
        if not provider_available(spec.provider):
            continue
        if available_providers and spec.provider not in available_providers:
            continue
        if required_context and spec.context < required_context:
            continue
        if max_cost_per_1k is not None and spec.cost_per_1k_in > max_cost_per_1k:
            continue
        candidates.append((name, spec))

    if not candidates:
        # Fall back to a declared free model even if no key is configured;
        # the caller will degrade gracefully on the actual call.
        name = "mistralai/mistral-7b"
        return SelectedModel(name, MODEL_CATALOG[name],
                             "no configured provider; free fallback", strategy)

    def score(item):
        name, spec = item
        cost = spec.cost_per_1k_in + spec.cost_per_1k_out
        speed = {"fast": 0, "medium": 1, "slow": 2}.get(spec.latency_hint, 1)
        quality = len(spec.strengths)
        if strategy == RoutingStrategy.CHEAPEST:
            return (cost, speed, name)
        if strategy == RoutingStrategy.FASTEST:
            return (speed, cost, name)
        if strategy == RoutingStrategy.BEST_QUALITY:
            return (-quality, cost, name)
        if strategy == RoutingStrategy.BALANCED:
            return (cost * 100 + speed, -quality, name)
        want = task if task != "general" else "general"
        bonus = -2 if want in spec.strengths or (want == "code" and "code" in spec.strengths) else 0
        return (bonus + cost * 10 + speed * 0.1, -quality, name)

    name, spec = sorted(candidates, key=score)[0]
    return SelectedModel(name, spec,
                         f"task={task}; strategy={strategy.value}; cost={spec.cost_per_1k_in}",
                         strategy)
