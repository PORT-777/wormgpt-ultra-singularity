"""
Plugin Runtime - Backward-compatible wrapper around PluginBroker.
Maintains the original interface (execute_tool, get_user_tools, execute)
while delegating credential resolution and mock mode to the broker.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from plugins_system.broker import PluginBroker
from plugins_system.store import JsonFilePluginStore
from plugins_system.auth import CredentialEncryption
from plugins_system.registry import registry_instance

logger = logging.getLogger("PluginRuntime")


class PluginExecutionError(Exception):
    """Raised when a plugin tool fails execution."""

    def __init__(self, plugin_id: str, message: str, original: Optional[Exception] = None):
        super().__init__(message)
        self.plugin_id = plugin_id
        self.message = message
        self.original = original


class PluginRuntime:
    """
    Backward-compatible wrapper around PluginBroker.
    Provides the same interface as before but delegates to the broker.
    """

    def __init__(self, db: Optional[JsonFilePluginStore] = None,
                 encryption_service: Optional[CredentialEncryption] = None):
        self.broker = PluginBroker()
        self.db = db
        self.encryption = encryption_service

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool call through the broker."""
        return await self.broker.execute(tool_name, parameters)

    async def execute_tool(self, user_id: str, tool_name: str,
                           parameters: Dict[str, Any]) -> Any:
        """
        Execute a plugin tool for a specific user.
        Resolves stored credentials first, then delegates to broker.
        """
        try:
            plugin_id, _ = self._parse_tool_name(tool_name)
        except ValueError:
            raise PluginExecutionError(tool_name, f"Invalid tool name: {tool_name}")

        # Try to load stored credentials for this user/plugin
        if self.db and self.encryption:
            try:
                stored = await self.db.get_plugin_credentials(user_id, plugin_id)
                if stored:
                    creds = self.encryption.decrypt(stored)
                    # Override broker credential resolution with stored creds
                    self.broker._stored_credentials = getattr(self.broker, '_stored_credentials', {})
                    self.broker._stored_credentials[f"{user_id}:{plugin_id}"] = creds
            except Exception as exc:
                logger.debug("credential lookup failed for %s/%s: %s", user_id, plugin_id, exc)

        try:
            # user_id is required so the broker can refresh and apply OAuth
            # credentials for linked accounts (per-user isolation).
            result = await self.broker.execute(tool_name, parameters, user_id=user_id)
            return result
        except Exception as exc:
            raise PluginExecutionError(plugin_id, str(exc), original=exc)

    async def get_user_tools(self, user_id: str) -> List[Dict[str, Any]]:
        """Return tool definitions for all plugins installed+enabled for user."""
        all_tools = self.broker.get_all_tool_definitions()
        if not self.db:
            return all_tools

        try:
            installed = await self.db.get_user_plugins(user_id, enabled_only=True)
            installed_ids = {r.plugin_id for r in installed}
            return [t for t in all_tools
                    if t.get("function", {}).get("name", "").split(".")[0] in installed_ids]
        except Exception as exc:
            logger.warning("get_user_tools failed: %s", exc)
            return all_tools

    def _parse_tool_name(self, tool_name: str) -> Tuple[str, str]:
        """Convert 'plugin.method' to (plugin_id, method_name)."""
        if "." not in tool_name:
            raise ValueError(
                f"Invalid tool name format: '{tool_name}'. "
                "Must be 'plugin_id.method_name'"
            )
        parts = tool_name.split(".")
        return parts[0], ".".join(parts[1:])

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Generate tool definitions via the broker."""
        return self.broker.get_all_tool_definitions()

    def get_plugin_names(self) -> List[str]:
        """Return list of all registered plugin IDs."""
        return [m["id"] for m in self.broker.registry.get_all_manifests()]


# Singleton shared with the FastAPI layer
def _make_runtime():
    store = JsonFilePluginStore("data/plugins.json")
    enc = CredentialEncryption()
    return PluginRuntime(db=store, encryption_service=enc)


runtime = _make_runtime()


def get_runtime() -> PluginRuntime:
    return runtime