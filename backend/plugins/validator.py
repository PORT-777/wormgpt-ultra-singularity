import logging
from typing import Any, Dict, List, Optional, Type
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool

logger = logging.getLogger("PluginValidator")

class PluginValidationError(Exception):
    """Raised when a plugin fails validation checks."""
    def __init__(self, plugin_id: str, errors: List[str]):
        self.plugin_id = plugin_id
        self.errors = errors
        super().__init__(f"Plugin {plugin_id} validation failed: {', '.join(errors)}")

class PluginValidator:
    """
    A deep inspection engine that validates plugin structure, manifest integrity,
    and tool compatibility before the plugin is allowed into the registry.
    """

    VALID_CATEGORIES = [
        "security", "social", "productivity", "communication",
        "devops", "cloud", "siem", "custom"
    ]

    VALID_AUTH_TYPES = ["apikey", "oauth2", "webhook", "none"]

    def __init__(self):
        pass

    async def validate_plugin_class(self, plugin_cls: Type[BasePlugin]) -> Dict[str, Any]:
        """
        Performs a full structural validation of a plugin class.
        Returns a validation report.
        """
        errors = []
        warnings = []

        # 1. Check if class inherits from BasePlugin
        if not issubclass(plugin_cls, BasePlugin):
            errors.append("Class does not inherit from BasePlugin.")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # 2. Validate Manifest
        manifest_errors, manifest_warnings = self._validate_manifest(plugin_cls.manifest)
        errors.extend(manifest_errors)
        warnings.extend(manifest_warnings)

        # 3. Validate Tool implementations match Manifest declarations
        tool_errors = self._validate_tools_match_implementation(plugin_cls)
        errors.extend(tool_errors)

        # 4. Check for required methods
        method_errors = self._validate_required_methods(plugin_cls)
        errors.extend(method_errors)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "plugin_id": plugin_cls.manifest.id
        }

    def _validate_manifest(self, manifest: PluginManifest) -> tuple:
        errors = []
        warnings = []

        if not manifest.id or len(manifest.id) < 3:
            errors.append("Plugin ID is missing or too short.")

        if manifest.category not in self.VALID_CATEGORIES:
            errors.append(f"Invalid category: {manifest.category}. Allowed: {self.VALID_CATEGORIES}")

        if manifest.auth_type not in self.VALID_AUTH_TYPES:
            errors.append(f"Invalid auth_type: {manifest.auth_type}. Allowed: {self.VALID_AUTH_TYPES}")

        if not manifest.name:
            errors.append("Plugin name is missing.")

        if not manifest.version:
            warnings.append("Plugin version is missing.")

        if not manifest.tools:
            warnings.append("Plugin declares zero tools.")

        return errors, warnings

    def _validate_tools_match_implementation(self, plugin_cls: Type[BasePlugin]) -> List[str]:
        errors = []
        manifest_tools = {tool.name for tool in plugin_cls.manifest.tools}

        # We can't easily inspect async execute() internals for every tool,
        # but we can ensure that the tool names follow the plugin_id.prefix convention.
        prefix = plugin_cls.manifest.id + "."
        for tool_name in manifest_tools:
            if not tool_name.startswith(prefix):
                errors.append(f"Tool name '{tool_name}' does not start with required prefix '{plugin_cls.manifest.id}.'")

        return errors

    def _validate_required_methods(self, plugin_cls: Type[BasePlugin]) -> List[str]:
        errors = []
        
        required_methods = ["_validate_credentials", "execute"]
        for method in required_methods:
            if not hasattr(plugin_cls, method) or not callable(getattr(plugin_cls, method)):
                errors.append(f"Missing required method: {method}")

        return errors

    async def validate_all_discovered_plugins(self, registry: Dict[str, Type[BasePlugin]]) -> Dict[str, Dict]:
        """
        Validates all plugins currently in the registry.
        Returns a mapping of plugin_id to validation report.
        """
        reports = {}
        for plugin_id, plugin_cls in registry.items():
            try:
                report = await self.validate_plugin_class(plugin_cls)
                reports[plugin_id] = report
                if not report["valid"]:
                    logger.error(f"Validation failed for {plugin_id}: {report['errors']}")
            except Exception as e:
                logger.error(f"Exception during validation of {plugin_id}: {str(e)}")
                reports[plugin_id] = {"valid": False, "errors": [str(e)], "warnings": [], "plugin_id": plugin_id}
        
        return reports
