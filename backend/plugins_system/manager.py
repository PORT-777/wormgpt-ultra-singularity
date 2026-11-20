import logging
from typing import Any, Dict, List, Optional

from plugins_system.registry import registry_instance, get_plugin_from_registry

logger = logging.getLogger("PluginManager")


class PluginManager:
    """
    Lifecycle operations for plugins: browse, install, authenticate,
    enable/disable, uninstall, and query installed state.
    """

    def __init__(self, db, encryption_service):
        self.db = db
        self.encryption = encryption_service

    # ------------------------------------------------------------------ catalog

    def list_available_plugins(self) -> List[Dict[str, Any]]:
        """All plugins discovered + validated in the registry, as manifests."""
        return registry_instance.get_all_manifests()

    async def get_installed_plugins(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns installed plugins, merged with their manifest so the UI has
        names, icons, and auth info in one payload.
        """
        installs = await self.db.get_user_plugins(user_id, enabled_only=False)
        manifests = {m["id"]: m for m in registry_instance.get_all_manifests()}
        result: List[Dict[str, Any]] = []

        for record in installs:
            manifest = manifests.get(record.plugin_id)
            if not manifest:
                continue
            result.append(
                {
                    **manifest,
                    "is_installed": True,
                    "is_enabled": record.is_enabled,
                    "installed_at": record.installed_at,
                    "last_used_at": record.last_used_at,
                }
            )
        return result

    # ----------------------------------------------------------------- installs

    async def install_plugin(self, user_id: str, plugin_id: str) -> bool:
        plugin_cls = await get_plugin_from_registry(plugin_id)
        if not plugin_cls:
            logger.warning("Install rejected — unknown plugin: %s", plugin_id)
            return False

        existing = await self.db.get_user_plugin(user_id, plugin_id)
        if existing:
            return True

        return await self.db.create_user_plugin(user_id, plugin_id)

    async def enable_plugin(self, user_id: str, plugin_id: str) -> bool:
        return await self.db.update_user_plugin_status(user_id, plugin_id, enabled=True)

    async def disable_plugin(self, user_id: str, plugin_id: str) -> bool:
        return await self.db.update_user_plugin_status(user_id, plugin_id, enabled=False)

    async def uninstall_plugin(self, user_id: str, plugin_id: str) -> bool:
        removed = await self.db.delete_user_plugin(user_id, plugin_id)
        if removed:
            await self.db.delete_plugin_credentials(user_id, plugin_id)
        return removed

    # --------------------------------------------------------------------- auth

    async def authenticate_plugin(
        self, user_id: str, plugin_id: str, credentials: Dict[str, Any]
    ) -> bool:
        """
        Validates credentials through the plugin's own _validate_credentials(),
        then stores them encrypted at rest.
        """
        plugin_cls = await get_plugin_from_registry(plugin_id)
        if not plugin_cls:
            return False

        # Probe instantiation — this runs the plugin's validation logic.
        try:
            plugin_cls(credentials)
        except Exception as exc:
            logger.warning("Credential validation failed for %s: %s", plugin_id, exc)
            return False

        encrypted = self.encryption.encrypt(credentials)
        return await self.db.save_plugin_credentials(user_id, plugin_id, encrypted)

    async def test_connection(
        self, user_id: str, plugin_id: str, credentials: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Attempts a live connection test. Uses supplied credentials if given,
        otherwise falls back to stored credentials.
        """
        plugin_cls = await get_plugin_from_registry(plugin_id)
        if not plugin_cls:
            return {"status": "error", "message": "Plugin not registered"}

        try:
            if credentials is None:
                stored = await self.db.get_plugin_credentials(user_id, plugin_id)
                if stored:
                    credentials = self.encryption.decrypt(stored)
                else:
                    # OAuth-linked accounts keep tokens in the integration store,
                    # never in the legacy plugin credential slot.
                    try:
                        from integrations.deps import get_oauth_service

                        service = get_oauth_service()
                        await service.ensure_fresh(user_id, plugin_id)
                        credentials = service.get_credentials_sync(user_id, plugin_id)
                    except Exception as exc:
                        logger.debug("OAuth credential lookup failed: %s", exc)
                        credentials = None

                if credentials is None:
                    # Public / keyless plugins run with an empty credential bag.
                    if plugin_cls.manifest.auth_type == "none":
                        credentials = {}
                    else:
                        return {
                            "status": "error",
                            "message": "Not connected. Authorize this integration first.",
                        }

            instance = plugin_cls(credentials)
            return await instance.test_connection()
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
