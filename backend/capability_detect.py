"""Model capability detection: infer capabilities from provider/model name."""
from __future__ import annotations

from typing import Set

CAP_RULES = {
    "gpt-4o": {"text", "image_analysis", "tool_calling", "structured_output", "streaming", "reasoning"},
    "gpt-4-vision": {"text", "image_analysis", "streaming"},
    "gemini": {"text", "image_analysis", "audio_input", "tool_calling", "streaming"},
    "claude": {"text", "image_analysis", "tool_calling", "reasoning", "streaming"},
    "llama": {"text", "streaming", "tool_calling"},
    "qwen": {"text", "image_analysis", "streaming", "tool_calling"},
    "dall-e": {"image_gen"},
    "stable-diffusion": {"image_gen"},
    "whisper": {"audio_input"},
    "tts": {"audio_output"},
}


def detect(model: str, provider: str = "") -> Set[str]:
    low = (model + " " + provider).lower()
    caps: Set[str] = {"text", "streaming"}
    for key, c in CAP_RULES.items():
        if key in low:
            caps |= c
    if "vision" in low or "vl" in low:
        caps.add("image_analysis")
    if "audio" in low:
        caps.add("audio_input")
    return caps


def detect_all(models: list) -> dict:
    return {m: sorted(detect(m)) for m in models}
