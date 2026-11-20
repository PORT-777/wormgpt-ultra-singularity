"""Compatibility shim for backend.plugins.sdk."""
from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool  # noqa: F401

__all__ = ["BasePlugin", "PluginManifest", "PluginTool"]
