"""Internal external-API integration subsystem.

Additive only: no existing route or frontend file is modified.
Every service is optional and fails closed when its key is missing.
"""
from __future__ import annotations

from .base import ExternalService
from .cache import TTLCache, cache
from .client import ExternalAPIError, ExternalClient, client
from .config import ExternalConfig, config
from .health import check_all, health_dashboard
from .rate_limiter import RateLimiter, limiter
from .registry import ServiceSpec, Registry, registry
from .services.ai import register_ai_services
from .services.data import register_data_services

_registered = False


def ensure_registered() -> None:
    global _registered
    if _registered:
        return
    register_ai_services()
    register_data_services()
    _registered = True


ensure_registered()

__all__ = [
    "ExternalService", "ExternalClient", "ExternalAPIError", "client",
    "TTLCache", "cache", "RateLimiter", "limiter", "ServiceSpec", "Registry",
    "registry", "config", "ExternalConfig", "check_all", "health_dashboard",
    "ensure_registered",
]
