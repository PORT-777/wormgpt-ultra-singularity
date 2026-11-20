"""Compatibility package: backend.plugins -> plugins_system.

The catalog, integrations, tests and broker all use plugins_system as the single
source of truth. This package keeps the older ``backend.plugins.*`` import paths
working without creating a second registry.
"""
from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool  # noqa: F401
from plugins_system.registry import (  # noqa: F401
    PLUGIN_REGISTRY,
    get_plugin_from_registry,
    register_plugin,
    registry_instance,
)
from plugins_system.runtime import PluginExecutionError  # noqa: F401

# Legacy marketplace API kept for the older module-level tests.
_MARKETPLACE: dict = {}


def register(manifest: dict) -> dict:
    pid = manifest.get("id") or manifest.get("name") or str(len(_MARKETPLACE) + 1)
    record = {"id": pid, **manifest}
    _MARKETPLACE[pid] = record
    return record


def get(pid: str):
    return _MARKETPLACE.get(pid)


def list_all():
    return list(_MARKETPLACE.values())


def enable(pid: str) -> bool:
    record = _MARKETPLACE.get(pid)
    if not record:
        return False
    record["enabled"] = True
    return True


def disable(pid: str) -> bool:
    record = _MARKETPLACE.get(pid)
    if not record:
        return False
    record["enabled"] = False
    return True


def uninstall(pid: str) -> bool:
    return _MARKETPLACE.pop(pid, None) is not None


def update_config(pid: str, config: dict):
    record = _MARKETPLACE.get(pid)
    if not record:
        return None
    record.setdefault("config", {}).update(config or {})
    return record


__all__ = [
    "BasePlugin", "PluginManifest", "PluginTool", "PLUGIN_REGISTRY",
    "get_plugin_from_registry", "register_plugin", "registry_instance",
    "PluginExecutionError", "register", "get", "list_all",
    "enable", "disable", "uninstall", "update_config",
]
