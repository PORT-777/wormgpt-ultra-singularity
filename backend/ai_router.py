"""AI router: picks best model for a task, respecting manual override."""
from __future__ import annotations

from typing import Optional, Tuple

from model_registry import REGISTRY, ModelSpec

# Task -> preferred capability set (ordered)
TASK_CAPS = {
    "image_analysis": {"image_analysis"},
    "image_gen": {"image_gen"},
    "audio": {"audio_input", "audio_output"},
    "code": {"text", "tool_calling"},
    "research": {"text", "web_search"},
    "default": {"text"},
}


class AIRouter:
    def route(self, task: str, manual_model: Optional[str] = None,
              user_prefs: Optional[dict] = None) -> Tuple[Optional[ModelSpec], str]:
        # Manual override always wins
        if manual_model:
            m = REGISTRY.get(manual_model)
            if m and m.enabled:
                return m, "manual"
        caps = TASK_CAPS.get(task, TASK_CAPS["default"])
        candidates = [m for m in REGISTRY.list() if caps.issubset(m.capabilities or set()) or caps <= m.capabilities]
        if not candidates:
            candidates = REGISTRY.list()
        if not candidates:
            return None, "no-models"
        # Score: quality proxy = context window + capability count - cost
        def score(m: ModelSpec) -> float:
            s = (m.context_window / 1000.0) + len(m.capabilities) * 2
            s -= (m.cost_input_per_1k + m.cost_output_per_1k) * 10
            if user_prefs and user_prefs.get("preferred_provider") == m.provider:
                s += 5
            return s
        best = max(candidates, key=score)
        return best, "auto"

    def check_compatibility(self, model_id: str, content_type: str) -> bool:
        m = REGISTRY.get(model_id)
        if not m:
            return False
        mapping = {
            "image": "image_analysis", "audio": "audio_input",
            "file": "file_analysis", "text": "text",
        }
        cap = mapping.get(content_type, "text")
        return m.supports(cap)


ROUTER = AIRouter()
