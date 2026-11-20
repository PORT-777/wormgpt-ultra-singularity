"""Compatibility shim for backend.plugins.store."""
from plugins_system.store import JsonFilePluginStore  # noqa: F401

InMemoryPluginStore = JsonFilePluginStore

__all__ = ["JsonFilePluginStore", "InMemoryPluginStore"]
