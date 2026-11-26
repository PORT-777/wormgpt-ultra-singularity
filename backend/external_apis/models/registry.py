"""Registry of configured local + API models."""
from __future__ import annotations

from ..config import config


def list_models():
    out = []
    for name, key in (("openai", "OPENAI_API_KEY"), ("cohere", "COHERE_API_KEY"),
                      ("openrouter", "OPENROUTER_API_KEY"), ("groq", "GROQ_API_KEY"),
                      ("gemini", "GEMINI_API_KEY")):
        out.append({"name": name, "configured": bool(config.key(key) or config.keys.get(key))})
    return out
