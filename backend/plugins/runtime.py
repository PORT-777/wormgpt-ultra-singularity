import asyncio
import logging
import traceback
import time
from typing import Dict, List, Any, Optional, Type
from datetime import datetime

from backend.plugins.sdk import BasePlugin
from backend.plugins.registry import PLUGIN_REGISTRY, get_plugin_from_registry
from backend.plugins.auditor import PluginAuditor

# Configure dedicated logger for plugin runtime
logger = logging.getLogger("PluginRuntime")

class PluginExecutionError(Exception):
    """Custom exception for errors occurring during plugin tool execution."""
    def __init__(self, tool_name: str, plugin_id: str, message: str, original_exception: Exception = None):
        self.tool_name = tool_name
        self.plugin_id = plugin_id
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

class PluginRuntime:
    """
    A robust, fault-tolerant runtime for executing plugin tool calls.
    Implements sandboxing concepts and comprehensive error boundaries.
    """

    def __init__(self, db, encryption_service):
        self.db = db
        self.encryption = encryption_service
        self.auditor = PluginAuditor(db)
        self._plugins: Dict[str, BasePlugin] = {}

    async def get_user_tools(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetches all tool definitions for a user's active plugins.
        Ensures that even if a plugin is partially broken, others are returned.
        """
        try:
            installed = await self.db.get_user_plugins(user_id, enabled_only=True)
        except Exception as e:
            logger.error(f"Failed to fetch user plugins from DB: {str(e)}")
            return []

        tools = []
        for plugin_install in installed:
            try:
                plugin = await self._load_plugin(user_id, plugin_install.plugin_id)
                if plugin:
                    for tool in plugin.manifest.tools:
                        # Convert Pydantic model to dict for LLM consumption
                        tool_dict = tool.model_dump()
                        # Standardize tool name to include plugin prefix
                        tool_dict["name"] = f"{plugin.manifest.id}.{tool.name}"
                        tools.append(tool_dict)
            except Exception as e:
                logger.error(f"Error loading tools for plugin {plugin_install.plugin_id}: {str(e)}")
                continue
        return tools

    async def execute_tool(
        self,
        user_id: str,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Executes a tool call within a protected error boundary.
        Prevents plugin crashes from killing the agent's stream.
        """
        plugin_id = tool_name.split('.')[0]
        start_time = time.perf_counter()
        
        try:
            plugin = await self._load_plugin(user_id, plugin_id)
            if not plugin:
                raise PluginExecutionError(tool_name, plugin_id, "Plugin not found or failed to load.")

            logger.info(f"User {user_id} calling {tool_name} with params: {parameters}")

            # Implement the actual execution with a timeout to prevent hanging
            result = await asyncio.wait_for(
                plugin.execute(tool_name, parameters),
                timeout=30.0  # 30 second hard limit per tool call
            )

            duration_ms = (time.perf_counter() - start_time) * 1000
            await self.auditor.record_telemetry(
                user_id=user_id,
                plugin_id=plugin_id,
                tool_name=tool_name,
                parameters=parameters,
                status="success",
                duration_ms=duration_ms
            )
            return result

        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = "Plugin tool execution timed out (30s limit)."
            logger.error(f"Timeout: {tool_name} for user {user_id}")
            await self.auditor.record_telemetry(
                user_id=user_id,
                plugin_id=plugin_id,
                tool_name=tool_name,
                parameters=parameters,
                status="error",
                duration_ms=duration_ms,
                error_details=error_msg
            )
            raise PluginExecutionError(tool_name, plugin_id, error_msg)

        except PluginExecutionError as p_err:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await self.auditor.record_telemetry(
                user_id=user_id,
                plugin_id=plugin_id,
                tool_name=tool_name,
                parameters=parameters,
                status="error",
                duration_ms=duration_ms,
                error_details=p_err.message
            )
            raise p_err

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_trace = traceback.format_exc()
            error_msg = f"Unhandled plugin exception: {str(e)}"
            logger.error(f"CRITICAL PLUGIN ERROR: {error_trace}")
            
            await self.auditor.record_telemetry(
                user_id=user_id,
                plugin_id=plugin_id,
                tool_name=tool_name,
                parameters=parameters,
                status="error",
                duration_ms=duration_ms,
                error_details=error_msg
            )
            raise PluginExecutionError(tool_name, plugin_id, error_msg, original_exception=e)

    async def _load_plugin(self, user_id: str, plugin_id: str) -> Optional[BasePlugin]:
        """
        Loads and caches plugin instances. 
        Uses user-specific credentials to instantiate the plugin.
        """
        cache_key = f"{user_id}:{plugin_id}"

        if cache_key not in self._plugins:
            plugin_class = await get_plugin_from_registry(plugin_id)
            if not plugin_class:
                return None
            
            try:
                credentials = await self._get_credentials(user_id, plugin_id)
                self._plugins[cache_key] = plugin_class(credentials)
            except Exception as e:
                logger.error(f"Failed to instantiate plugin {plugin_id} for user {user_id}: {e}")
                return None

        return self._plugins[cache_key]

    async def _get_credentials(self, user_id: str, plugin_id: str) -> Dict[str, Any]:
        """Fetches and decrypts user's plugin credentials from DB."""
        encrypted = await self.db.get_plugin_credentials(user_id, plugin_id)
        if not encrypted:
            raise ValueError(f"No credentials found for plugin {plugin_id}")
        return self.encryption.decrypt(encrypted)
