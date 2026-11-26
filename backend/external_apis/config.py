"""Typed configuration for the internal external-API subsystem.

Loads keys from env (never from source), validates at startup by warning —
not crashing — when an optional key is missing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

_KEY_NAMES = (
    "OPENAI_API_KEY", "COHERE_API_KEY", "HUGGINGFACE_API_KEY", "NLPCLOUD_API_KEY",
    "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "ASSEMBLYAI_API_KEY", "GLADIA_API_KEY",
    "CLARIFAI_API_KEY", "IMAGGA_API_KEY", "ROBOFLOW_API_KEY", "IRISNET_API_KEY",
    "GOOGLE_SPEECH_API_KEY", "SERPAPI_KEY", "WOLFRAM_APP_ID", "PERSPECTIVE_API_KEY",
    "DIALOGFLOW_PROJECT_ID", "WITAI_TOKEN", "EDENAI_API_KEY", "GITHUB_TOKEN",
    "NEWS_API_KEY", "OPENWEATHER_API_KEY", "NASA_API_KEY", "AIMLAPI_API_KEY",
    "XIUROUTER_API_KEY", "UNOROUTER_API_KEY", "SPAMHUNTER_API_KEY",
    "CUSTOMGPT_API_KEY", "SNAPRENDER_API_KEY", "TRANSCRIPTFETCH_API_KEY",
    "FIN_SIGNALS_API_KEY", "GAND_R_API_KEY", "WAVESPEED_API_KEY", "INFERDO_API_KEY",
    "SKYBIOMETRY_API_KEY", "CLOUDMERSIVE_API_KEY", "SUMMARIZE_AI_API_KEY",
    "CRAWL4AI_API_KEY", "INTERNAL_API_KEY",
)


@dataclass
class ExternalConfig:
    keys: Dict[str, str] = field(default_factory=dict)
    timeout_s: float = 20.0
    max_retries: int = 2
    cache_ttl_s: float = 300.0
    cache_max_entries: int = 1024
    rate_limit_per_min: int = 100
    internal_key: str = ""

    @classmethod
    def from_env(cls) -> "ExternalConfig":
        keys = {name: os.getenv(name, "").strip() for name in _KEY_NAMES}
        return cls(
            keys=keys,
            timeout_s=float(os.getenv("EXTERNAL_API_TIMEOUT", "20") or 20),
            max_retries=int(os.getenv("EXTERNAL_API_RETRIES", "2") or 2),
            cache_ttl_s=float(os.getenv("EXTERNAL_CACHE_TTL", "300") or 300),
            rate_limit_per_min=int(os.getenv("EXTERNAL_RATE_LIMIT", "100") or 100),
            internal_key=keys.get("INTERNAL_API_KEY", ""),
        )

    def key(self, name: str) -> str:
        return self.keys.get(name, "")

    def missing(self) -> List[str]:
        return sorted(name for name, value in self.keys.items()
                      if name != "INTERNAL_API_KEY" and not value)


config = ExternalConfig.from_env()
