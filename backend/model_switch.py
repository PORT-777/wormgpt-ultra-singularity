"""Model switching helper: preserve history, trim to new context window, warn on incompatibility."""
from __future__ import annotations

from typing import List, Dict, Tuple

from context_manager import total_tokens
from model_registry import REGISTRY


def switch(old_model: str, new_model: str, messages: List[Dict],
           content_type: str = "text") -> Tuple[List[Dict], dict]:
    new_spec = REGISTRY.get(new_model)
    old_spec = REGISTRY.get(old_model)
    info = {"old": old_model, "new": new_model, "trimmed": False,
            "warning": None, "compatible": True}
    if not new_spec:
        info["warning"] = "unknown target model"
        return messages, info
    # compatibility check
    cap_map = {"image": "image_analysis", "audio": "audio_input",
               "file": "file_analysis", "text": "text"}
    cap = cap_map.get(content_type, "text")
    if not new_spec.supports(cap):
        info["compatible"] = False
        info["warning"] = f"{new_model} does not support {content_type}"
    # trim to new context window
    if total_tokens(messages) > new_spec.context_window * 0.9:
        # keep system + last turns
        sys_msgs = [m for m in messages if m.get("role") == "system"]
        others = [m for m in messages if m.get("role") != "system"]
        # trim oldest until fits
        while others and total_tokens(sys_msgs + others) > new_spec.context_window * 0.8:
            others.pop(0)
        messages = sys_msgs + others
        info["trimmed"] = True
    return messages, info
