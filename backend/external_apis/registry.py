"""Declarative central registry for every external API integration.

A ServiceSpec describes auth style, endpoints per action and an optional
response transform. Behaviour is shared in base.py; no 50-copy paste.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .config import config


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    category: str
    base_url: str
    endpoints: Dict[str, str]
    key_env: str = ""
    auth_style: str = "none"          # none | bearer | query | header
    key_param: str = "key"
    health_path: str = ""
    default_action: str = "query"
    method: str = "GET"
    transform: Optional[Callable[[Any], Any]] = None

    def available(self) -> bool:
        return not self.key_env or bool(config.key(self.key_env))

    def headers(self) -> Dict[str, str]:
        if self.auth_style == "bearer" and config.key(self.key_env):
            return {"Authorization": f"Bearer {config.key(self.key_env)}"}
        if self.auth_style == "header" and config.key(self.key_env):
            return {self.key_param: config.key(self.key_env)}
        return {}

    def url(self, action: str, **parts: Any) -> str:
        template = self.endpoints.get(action) or self.endpoints.get(self.default_action)
        if not template:
            raise KeyError(f"{self.name}: unknown action {action}")
        try:
            return template.format(**parts, base=self.base_url)
        except KeyError:
            return template


class Registry:
    def __init__(self) -> None:
        self._services: Dict[str, ServiceSpec] = {}

    def register(self, spec: ServiceSpec) -> ServiceSpec:
        self._services[spec.name] = spec
        return spec

    def get(self, name: str) -> Optional[ServiceSpec]:
        return self._services.get(name)

    def all(self) -> List[ServiceSpec]:
        return sorted(self._services.values(), key=lambda s: (s.category, s.name))

    def status(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name, "category": s.category,
                "available": s.available(),
                "key_configured": bool(s.key_env and config.key(s.key_env)),
                "actions": sorted(s.endpoints),
            }
            for s in self.all()
        ]


registry = Registry()
