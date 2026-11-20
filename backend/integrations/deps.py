"""Process singletons for the OAuth integration subsystem."""

from __future__ import annotations

from pathlib import Path

from integrations.service import OAuthService
from integrations.store import IntegrationStore
from plugins_system.deps import encryption

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_STORE_PATH = _BACKEND_DIR / "data" / "integrations.json"

store = IntegrationStore(_STORE_PATH, encryption)
oauth_service = OAuthService(store)


def get_integration_store() -> IntegrationStore:
    return store


def get_oauth_service() -> OAuthService:
    return oauth_service


async def ensure_registry_discovered() -> None:
    """The catalog is discovered lazily once per process."""
    from plugins_system.registry import registry_instance

    if not registry_instance._plugins:
        await registry_instance.discover_plugins()
