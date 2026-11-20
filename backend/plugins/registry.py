"""Compatibility shim for backend.plugins.registry.

Discovery uses plugins_system's absolute catalog path, so it is independent of
the process working directory.
"""
from plugins_system.registry import (  # noqa: F401
    DEFAULT_CATALOG_PATH,
    PLUGIN_REGISTRY,
    PluginRegistry,
    get_plugin_from_registry,
    register_plugin,
    registry_instance,
)

__all__ = [
    "DEFAULT_CATALOG_PATH", "PLUGIN_REGISTRY", "PluginRegistry",
    "get_plugin_from_registry", "register_plugin", "registry_instance",
]
