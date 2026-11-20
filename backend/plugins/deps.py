"""
Single source of truth for plugin subsystem singletons.

Every API router and the app entrypoint import from here so the runtime,
manager, store, and encryption instance are created exactly once.
"""

from backend.plugins.auth import CredentialEncryption
from backend.plugins.manager import PluginManager
from backend.plugins.runtime import PluginRuntime
from backend.plugins.store import InMemoryPluginStore

# Persistence (swap for your real DB adapter — same async surface)
store = InMemoryPluginStore()

# Encryption (AES-256 over credentials at rest)
encryption = CredentialEncryption()

# Orchestration
manager = PluginManager(db=store, encryption_service=encryption)
runtime = PluginRuntime(db=store, encryption_service=encryption)


def get_store():
    return store


def get_manager() -> PluginManager:
    return manager


def get_runtime() -> PluginRuntime:
    return runtime
