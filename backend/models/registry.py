"""Model catalog with typed specs."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    context: int = 128000
    cost_per_1k_in: float = 0.0
    cost_per_1k_out: float = 0.0
    strengths: tuple[str, ...] = field(default_factory=tuple)
    latency_hint: str = "medium"


MODEL_CATALOG: dict[str, ModelSpec] = {
    "gpt-4o": ModelSpec("openai", 128000, 0.005, 0.015,
                        ("reasoning", "code", "vision"), "medium"),
    "gpt-4o-mini": ModelSpec("openai", 128000, 0.00015, 0.0006,
                             ("fast", "cheap", "general"), "fast"),
    "gpt-4-turbo": ModelSpec("openai", 128000, 0.01, 0.03,
                             ("reasoning", "long-context"), "slow"),
    "claude-3-5-sonnet": ModelSpec("anthropic", 200000, 0.003, 0.015,
                                   ("reasoning", "code", "long-context"), "medium"),
    "claude-3-haiku": ModelSpec("anthropic", 200000, 0.00025, 0.00125,
                                ("fast", "cheap"), "fast"),
    "meta-llama/llama-3.1-70b": ModelSpec("openrouter", 128000, 0.0005, 0.0007,
                                          ("open", "general"), "medium"),
    "google/gemini-flash-1.5": ModelSpec("openrouter", 1000000, 0.000075, 0.0003,
                                         ("long-context", "fast"), "fast"),
    "mistralai/mistral-7b": ModelSpec("openrouter", 32000, 0.0, 0.0,
                                      ("free", "general"), "medium"),
    "microsoft/phi-3-mini": ModelSpec("openrouter", 128000, 0.0, 0.0,
                                      ("free", "fast", "small"), "fast"),
    "qwen/qwen-2-72b": ModelSpec("openrouter", 128000, 0.0, 0.0,
                                 ("free", "multilingual"), "medium"),
    "hf/mistral-7b-instruct": ModelSpec("huggingface", 32000, 0.0, 0.0, ("free",)),
    "hf/zephyr-7b-beta": ModelSpec("huggingface", 32000, 0.0, 0.0, ("free", "chat")),
}

_PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY", "huggingface": "HUGGINGFACE_API_KEY",
}


def provider_available(provider: str) -> bool:
    key = _PROVIDER_KEYS.get(provider)
    if not key:
        return False
    return bool(os.getenv(key, "").strip())


def catalog(available_only: bool = False) -> dict[str, dict[str, Any]]:
    out = {}
    for name, spec in MODEL_CATALOG.items():
        if available_only and not provider_available(spec.provider):
            continue
        out[name] = {"provider": spec.provider, "context": spec.context,
                     "cost_per_1k_in": spec.cost_per_1k_in,
                     "cost_per_1k_out": spec.cost_per_1k_out,
                     "strengths": list(spec.strengths),
                     "available": provider_available(spec.provider)}
    return out
