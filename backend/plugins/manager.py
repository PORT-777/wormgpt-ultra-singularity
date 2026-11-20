"""Compatibility shim for backend.plugins.manager."""
from plugins_system.manager import PluginManager  # noqa: F401

__all__ = ["PluginManager"]
