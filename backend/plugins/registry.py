import os
import importlib.util
import logging
from typing import Dict, List, Any, Optional, Type
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.validator import PluginValidator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PluginRegistry")

class PluginRegistry:
    """
    Central store for all available plugins with dynamic auto-discovery and validation.
    """

    def __init__(self, catalog_path: str = "backend/plugins_catalog"):
        self.catalog_path = catalog_path
        self._plugins: Dict[str, Type[BasePlugin]] = {}
        self.validator = PluginValidator()

    async def discover_plugins(self):
        """
        Scans the catalog directory recursively and dynamically imports all plugin modules.
        Each plugin is validated before being registered.
        """
        logger.info(f"Starting plugin discovery in {self.catalog_path}...")
        
        if not os.path.exists(self.catalog_path):
            logger.error(f"Catalog path {self.catalog_path} does not exist.")
            return

        count = 0
        valid_count = 0
        
        for root, _, files in os.walk(self.catalog_path):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = os.path.join(root, file)
                    module_name = file[:-3]
                    
                    # Create a unique module name based on path to avoid collisions
                    rel_path = os.path.relpath(file_path, os.getcwd())
                    spec_module_name = rel_path.replace(os.path.sep, ".").rstrip(".py")

                    try:
                        self._import_plugin_module(spec_module_name, file_path)
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to load plugin from {file_path}: {str(e)}")

        # Run validation on all discovered plugins
        validation_reports = await self.validate_all_plugins()
        
        for plugin_id, report in validation_reports.items():
            if report["valid"]:
                valid_count += 1
            else:
                logger.error(f"Plugin {plugin_id} failed validation: {report['errors']}")

        logger.info(f"Discovery complete. Loaded {count} modules, {valid_count} valid plugins registered.")

    def _import_plugin_module(self, module_name: str, file_path: str):
        """
        Performs the dynamic import of a specific python file.
        """
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # After execution, the @register_plugin decorator will have populated PLUGIN_REGISTRY
            logger.debug(f"Module {module_name} imported successfully.")
        else:
            raise ImportError(f"Could not create spec for {module_name}")

    async def validate_all_plugins(self) -> Dict[str, Dict]:
        """Validates all plugins currently registered."""
        return await self.validator.validate_all_discovered_plugins(self._plugins)

    def get_all_manifests(self) -> List[Dict[str, Any]]:
        """Returns all loaded plugin manifests for the Store UI."""
        manifests = []
        for plugin_id, plugin_cls in self._plugins.items():
            try:
                manifests.append(plugin_cls.manifest.model_dump())
            except Exception as e:
                logger.error(f"Error extracting manifest for {plugin_id}: {e}")
        return manifests

    def register_plugin(self, plugin_cls: Type[BasePlugin]):
        """
        Registers a plugin class into the registry.
        """
        plugin_id = plugin_cls.manifest.id
        self._plugins[plugin_id] = plugin_cls
        logger.info(f"Registered plugin: {plugin_id}")
        return plugin_cls

    async def get_plugin_from_registry(self, plugin_id: str) -> Optional[Type[BasePlugin]]:
        """Retrieve a plugin class by its ID from the registry."""
        return self._plugins.get(plugin_id)

# Singleton instance for the application
registry_instance = PluginRegistry()

# Redefine the global registry for the rest of the app to use
PLUGIN_REGISTRY = registry_instance._plugins

def register_plugin(plugin_cls: Type[BasePlugin]):
    """
    Decorator to register a plugin class into the registry.
    """
    return registry_instance.register_plugin(plugin_cls)

async def get_plugin_from_registry(plugin_id: str) -> Optional[Type[BasePlugin]]:
    """Retrieve a plugin class by its ID from the registry."""
    return registry_instance._plugins.get(plugin_id)
