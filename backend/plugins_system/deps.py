"""
Single source of truth for plugin subsystem singletons.

Both the API router and the chat engine import from here, so the store,
encryption, manager, and runtime are constructed exactly once per process.
"""

from __future__ import annotations

from pathlib import Path

from plugins_system.auth import CredentialEncryption
from plugins_system.manager import PluginManager
from plugins_system.runtime import PluginRuntime
from plugins_system.store import JsonFilePluginStore

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_STORE_PATH = _BACKEND_DIR / "data" / "plugins.json"

# Persistence: swap for a SQL adapter by keeping the same async surface.
store = JsonFilePluginStore(_STORE_PATH)

# AES-256 (Fernet) at rest for credentials.
encryption = CredentialEncryption()

manager = PluginManager(db=store, encryption_service=encryption)
runtime = PluginRuntime(db=store, encryption_service=encryption)


def get_store() -> JsonFilePluginStore:
    return store


def get_manager() -> PluginManager:
    return manager


def get_runtime() -> PluginRuntime:
    return runtime
