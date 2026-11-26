"""Smart model routing by cost/speed/quality tradeoff."""
from __future__ import annotations


def choose(preference: str = "balanced"):
    order = {
        "cheap": ["groq", "openrouter", "openai", "gemini"],
        "fast": ["groq", "openrouter", "openai"],
        "quality": ["openai", "gemini", "openrouter", "groq"],
        "balanced": ["openrouter", "groq", "openai", "gemini"],
    }
    return order.get(preference, order["balanced"])
