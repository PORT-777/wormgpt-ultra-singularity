"""Base HTTP client with bounded retry, timeout and error normalization."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx

from .config import config


class ExternalAPIError(RuntimeError):
    def __init__(self, message: str, *, status: Optional[int] = None,
                 service: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.service = service


class ExternalClient:
    def __init__(self, cfg=config) -> None:
        self.cfg = cfg

    async def request(self, method: str, url: str, *,
                      service: str = "",
                      params: Optional[Dict[str, Any]] = None,
                      json_body: Optional[Dict[str, Any]] = None,
                      headers: Optional[Dict[str, str]] = None,
                      timeout: Optional[float] = None) -> Any:
        last: Optional[Exception] = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout or self.cfg.timeout_s,
                    headers={"User-Agent": "PORT777-InternalIntegration/1.0",
                             **(headers or {})},
                ) as client:
                    response = await client.request(
                        method, url, params=params, json=json_body)
                if response.status_code >= 400:
                    raise ExternalAPIError(
                        f"HTTP {response.status_code}: {response.text[:200]}",
                        status=response.status_code, service=service)
                try:
                    return response.json()
                except Exception:
                    return {"text": response.text[:2000]}
            except Exception as exc:
                last = exc
                if isinstance(exc, ExternalAPIError) and (exc.status or 0) < 500:
                    break
                if attempt < self.cfg.max_retries:
                    await asyncio.sleep(0.3 * (attempt + 1))
        raise ExternalAPIError(str(last), service=service)

    async def get(self, url: str, **kw) -> Any:
        return await self.request("GET", url, **kw)

    async def post(self, url: str, **kw) -> Any:
        return await self.request("POST", url, **kw)


client = ExternalClient()
