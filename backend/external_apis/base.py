"""Shared service behaviour: query(), healthCheck(), getCached()."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .cache import cache
from .client import client
from .registry import ServiceSpec


class ExternalService:
    def __init__(self, spec: ServiceSpec) -> None:
        self.spec = spec

    async def query(self, action: str, payload: Optional[Dict[str, Any]] = None,
                    **parts: Any) -> Any:
        payload = payload or {}
        spec = self.spec
        url = spec.url(action, **{**payload, **parts})
        params = dict(payload) if spec.method == "GET" else None
        if spec.auth_style == "query" and config_key(spec):
            params = params or {}
            params[spec.key_param] = config_key(spec)
        body = dict(payload) if spec.method == "POST" else None
        result = await client.request(
            spec.method, url, service=spec.name, params=params,
            json_body=body, headers=spec.headers())
        if spec.transform:
            result = spec.transform(result)
        return result

    async def healthCheck(self) -> Dict[str, Any]:
        if not self.spec.available():
            return {"status": "degraded", "reason": "missing api key",
                    "service": self.spec.name}
        if not self.spec.health_path:
            return {"status": "ok", "service": self.spec.name,
                    "reason": "keyed, no health endpoint"}
        try:
            await client.get(
                self.spec.health_path.format(base=self.spec.base_url),
                service=self.spec.name, headers=self.spec.headers())
            return {"status": "ok", "service": self.spec.name}
        except Exception as exc:
            return {"status": "degraded", "reason": str(exc)[:200],
                    "service": self.spec.name}

    async def getCached(self, action: str,
                        payload: Optional[Dict[str, Any]] = None) -> Any:
        key = cache.make_key(self.spec.name, action, payload or {})
        hit = cache.get(key)
        if hit is not None:
            return hit
        value = await self.query(action, payload)
        cache.set(key, value)
        return value


def config_key(spec: ServiceSpec) -> str:
    from .config import config
    return config.key(spec.key_env) if spec.key_env else ""
