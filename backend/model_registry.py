"""Model registry + capability detection.

Central, data-driven registry of providers/models and their capabilities.
Adding a model = adding an entry; no chat code changes.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set

CAPABILITIES = {
    "text", "image_gen", "image_analysis", "file_analysis",
    "audio_input", "audio_output", "live_voice", "web_search",
    "tool_calling", "reasoning", "structured_output", "streaming",
}


@dataclass
class ModelSpec:
    id: str
    provider: str
    name: str
    capabilities: Set[str] = field(default_factory=set)
    context_window: int = 8192
    max_output_tokens: int = 4096
    supports_temperature: bool = True
    supports_top_p: bool = True
    supports_reasoning_effort: bool = False
    cost_input_per_1k: float = 0.0
    cost_output_per_1k: float = 0.0
    enabled: bool = True

    def supports(self, cap: str) -> bool:
        return cap in self.capabilities

    def to_dict(self) -> dict:
        d = asdict(self)
        d["capabilities"] = sorted(self.capabilities)
        return d


class ModelRegistry:
    def __init__(self, path: Optional[Path] = None):
        self._models: Dict[str, ModelSpec] = {}
        self._path = path
        if path and path.exists():
            self.load(path)

    def register(self, spec: ModelSpec) -> None:
        self._models[spec.id] = spec

    def get(self, model_id: str) -> Optional[ModelSpec]:
        return self._models.get(model_id)

    def list(self, provider: Optional[str] = None, capability: Optional[str] = None) -> List[ModelSpec]:
        out = list(self._models.values())
        if provider:
            out = [m for m in out if m.provider == provider]
        if capability:
            out = [m for m in out if m.supports(capability)]
        return [m for m in out if m.enabled]

    def providers(self) -> List[str]:
        return sorted({m.provider for m in self._models.values()})

    def has_capability(self, model_id: str, cap: str) -> bool:
        m = self.get(model_id)
        return bool(m and m.supports(cap))

    def save(self, path: Optional[Path] = None) -> None:
        p = path or self._path
        if not p:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps([m.to_dict() for m in self._models.values()], indent=2))

    def load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text())
        except Exception:
            return
        for entry in data:
            caps = set(entry.pop("capabilities", []))
            self._models[entry["id"]] = ModelSpec(**entry, capabilities=caps)


# Singleton
_DEFAULT_PATH = Path(os.getenv("MODEL_REGISTRY_PATH", "")).expanduser() if os.getenv("MODEL_REGISTRY_PATH") else None
REGISTRY = ModelRegistry(_DEFAULT_PATH)
