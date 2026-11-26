"""Internal-only routes for the external-API subsystem.

Every route requires `x-internal-key` when INTERNAL_API_KEY is configured
(fail closed when unset -> routes return 503). No frontend calls these.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from .base import ExternalService
from .config import config
from .health import health_dashboard
from .registry import registry
from . import ensure_registered

log = logging.getLogger("external_apis_api")
ensure_registered()

router = APIRouter(prefix="/api/internal", tags=["internal-services"])


class QueryRequest(BaseModel):
    action: str = "query"
    payload: Dict[str, Any] = {}
    use_cache: bool = True


def _authorize(x_internal_key: Optional[str]) -> None:
    expected = config.internal_key
    if not expected:
        raise HTTPException(status_code=503, detail="internal services disabled")
    if x_internal_key != expected:
        raise HTTPException(status_code=401, detail="invalid internal key")


@router.get("/health/all")
async def all_health(x_internal_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    _authorize(x_internal_key)
    return await health_dashboard()


@router.get("/services")
async def list_services(x_internal_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    _authorize(x_internal_key)
    return {"count": len(registry.all()), "services": registry.status()}


@router.post("/services/{service}/query")
async def query_service(service: str, body: QueryRequest,
                        x_internal_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    _authorize(x_internal_key)
    spec = registry.get(service)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown service {service}")
    from .rate_limiter import limiter
    if not limiter.allow(service):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    try:
        impl = ExternalService(spec)
        value = (await impl.getCached(body.action, body.payload)
                 if body.use_cache else
                 await impl.query(body.action, body.payload))
        return {"service": service, "action": body.action, "available": True,
                "result": value}
    except Exception as exc:
        log.warning("service %s failed: %s", service, exc)
        return {"service": service, "action": body.action,
                "available": False, "reason": str(exc)[:300]}


@router.get("/services/{service}/health")
async def service_health(service: str,
                         x_internal_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    _authorize(x_internal_key)
    spec = registry.get(service)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown service {service}")
    return await ExternalService(spec).healthCheck()
