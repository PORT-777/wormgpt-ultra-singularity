"""
Plugin Broker - Centralized plugin execution engine.
Handles credential resolution, mock mode, and graceful fallbacks.
"""
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

from plugins_system.registry import registry_instance

logger = logging.getLogger("PluginBroker")


class PluginBroker:
    """
    Central broker that manages all plugin executions.
    Handles credential resolution, API routing, and graceful fallbacks.
    """

    def __init__(self):
        self.registry = registry_instance
        self._mock_mode = os.getenv("PLUGIN_MOCK_MODE", "true").lower() == "true"
        self._stored_credentials: Dict[str, Dict[str, str]] = {}

    async def execute(self, tool_name: str, parameters: Dict[str, Any],
                  user_id: Optional[str] = None) -> Any:
        """
        Executes a tool call through the appropriate plugin.
        Automatically resolves credentials and applies fallbacks.
        """
        try:
            plugin_id, method_name = self._parse_tool_name(tool_name)
            plugin_cls = self.registry.get(plugin_id)

            if not plugin_cls:
                raise ValueError(f"Plugin '{plugin_id}' not found in registry.")

            # OAuth-linked integrations: refresh before resolving credentials.
            # Imported lazily so the plugin subsystem has no hard dependency on
            # the integration layer (avoids an import cycle at boot).
            oauth_connected = False
            if user_id:
                try:
                    from integrations.deps import get_oauth_service

                    service = get_oauth_service()
                    await service.ensure_fresh(user_id, plugin_id)
                    oauth_connected = bool(
                        service.get_credentials_sync(user_id, plugin_id)
                    )
                except Exception as exc:
                    logger.debug("OAuth prepare failed for %s: %s", plugin_id, exc)

            # Resolve credentials dynamically from environment
            credentials = self._resolve_credentials(plugin_id, user_id=user_id)

            try:
                plugin = plugin_cls(credentials=credentials)
            except ValueError as cred_err:
                if self._mock_mode:
                    logger.warning(
                        f"Plugin '{plugin_id}' credential check failed: {cred_err}. "
                        "Running in MOCK mode."
                    )
                    return self._mock_response(tool_name, str(cred_err))
                else:
                    raise

            # In mock mode, intercept before real execution. A real OAuth link
            # always executes for real: the user explicitly authorized it.
            if (
                self._mock_mode
                and plugin_cls.manifest.auth_type != "none"
                and not oauth_connected
            ):
                logger.info(f"MOCK mode: intercepting {tool_name}")
                return self._mock_response(tool_name, "mock mode active")

            logger.info(f"Executing tool: {tool_name} via broker")
            result = await plugin.execute(tool_name, parameters)
            return result

        except Exception as e:
            logger.error(f"Broker error executing '{tool_name}': {str(e)}")
            if self._mock_mode:
                return self._mock_response(tool_name, str(e))
            raise e

    def _resolve_credentials(self, plugin_id: str, user_id: Optional[str] = None) -> Dict[str, str]:
        """
        Resolves API credentials from environment variables.
        Pattern: {PLUGIN_ID}_API_KEY, {PLUGIN_ID}_TOKEN, etc.
        Also checks stored credentials from the runtime layer.
        """
        prefix = plugin_id.upper()
        creds = {}

        # Check stored credentials first (from runtime.execute_tool)
        if user_id:
            stored = self._stored_credentials.get(f"{user_id}:{plugin_id}")
            if stored:
                creds.update(stored)

        # Common credential patterns
        for key_suffix in ["API_KEY", "TOKEN", "AUTH_TOKEN", "SECRET", "PASSWORD"]:
            env_key = f"{prefix}_{key_suffix}"
            val = os.getenv(env_key)
            if val:
                creds[key_suffix.lower()] = val

        # Plugin-specific known keys
        specific_keys = {
            "telegram": ["bot_token"],
            "twilio": ["account_sid", "auth_token", "from_number"],
            "sendgrid": ["api_key", "from_email"],
            "pushover": ["token", "user"],
            "matrix": ["access_token", "homeserver"],
            "jenkins": ["url", "username", "api_token"],
            "vercel": ["api_key", "team_id"],
            "sentry": ["auth_token", "org_slug"],
            "datadog": ["api_key", "app_key", "site"],
            "cloudflare": ["api_token"],
            "digitalocean": ["api_token"],
            "github": ["api_token", "default_owner"],
            "gitlab": ["api_token", "url"],
            "jira": ["api_token", "url", "email"],
            "notion": ["api_token"],
            "slack": ["bot_token"],
            "teams": ["app_id", "app_token"],
            "aws": ["access_key_id", "secret_access_key", "region"],
            "azure": ["client_id", "client_secret", "tenant_id"],
            "openai": ["api_key"],
            "anthropic": ["api_key"],
            "google": ["api_key"],
            "groq": ["api_key"],
            "deepseek": ["api_key"],
            "mistral": ["api_key"],
            "cohere": ["api_key"],
            "perplexity": ["api_key"],
        }

        for key in specific_keys.get(plugin_id, []):
            env_key = f"{prefix}_{key.upper()}"
            val = os.getenv(env_key)
            if val:
                creds[key] = val

        # OAuth credentials are authoritative: never let an old environment
        # key or a legacy stored key shadow an explicitly linked account.
        if user_id:
            try:
                from integrations.deps import get_oauth_service

                oauth_creds = get_oauth_service().get_credentials_sync(user_id, plugin_id)
                if oauth_creds:
                    creds.update(oauth_creds)
            except Exception as exc:
                logger.debug("OAuth credential resolution failed: %s", exc)

        return creds

    def _mock_response(self, tool_name: str, error: str) -> Dict[str, Any]:
        """Returns a mock response when in mock mode."""
        return {
            "status": "mock",
            "tool": tool_name,
            "message": "Running in PLUGIN_MOCK_MODE - no real API call made",
            "error": error,
        }

    def _parse_tool_name(self, tool_name: str) -> Tuple[str, str]:
        if "." not in tool_name:
            raise ValueError(
                f"Invalid tool name format: '{tool_name}'. "
                "Must be 'plugin_id.method_name'"
            )
        parts = tool_name.split(".")
        return parts[0], ".".join(parts[1:])

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Generates tool definitions compatible with OpenAI/Anthropic."""
        all_tools = []
        manifests = self.registry.get_all_manifests()
        for manifest in manifests:
            for tool in manifest.get("tools", []):
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": f"{manifest['id']}.{tool['name']}",
                        "description": tool.get("description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": tool.get("parameters", {}),
                            "required": list(tool.get("parameters", {}).keys()) if tool.get("parameters") else [],
                        },
                    },
                })
        logger.info(f"Generated {len(all_tools)} tool definitions")
        return all_tools