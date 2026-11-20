"""
Plugin registry with runtime auto-discovery.

Scans plugins_catalog/ (sibling of this package), imports every module, and lets
each @register_plugin decorator register itself. Every discovered plugin is then
validated before it is exposed to the manager or the agent.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from plugins_system.sdk import BasePlugin
from plugins_system.validator import PluginValidator

logger = logging.getLogger("PluginRegistry")

_HERE = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = _HERE.parent / "plugins_catalog"


class PluginRegistry:
    def __init__(self, catalog_path: Optional[Path] = None) -> None:
        self.catalog_path = Path(catalog_path or DEFAULT_CATALOG_PATH)
        self._plugins: Dict[str, Type[BasePlugin]] = {}
        self.validator = PluginValidator()

    # ---------------------------------------------------------------- discovery

    async def discover_plugins(self) -> None:
        if not self.catalog_path.exists():
            logger.error("catalog path missing: %s", self.catalog_path)
            return

        imported = 0
        for py_file in sorted(self.catalog_path.rglob("*.py")):
            if py_file.name.startswith("__"):
                continue
            rel = py_file.relative_to(self.catalog_path.parent).with_suffix("")
            module_name = ".".join(rel.parts)
            try:
                self._import_module(module_name, py_file)
                imported += 1
            except Exception as exc:  # a broken plugin must never kill startup
                logger.error("failed to import %s: %s", module_name, exc)

        reports = await self.validate_all_plugins()
        valid = [pid for pid, r in reports.items() if r["valid"]]
        invalid = {pid: r["errors"] for pid, r in reports.items() if not r["valid"]}
        for pid, errs in invalid.items():
            logger.warning("plugin rejected (%s): %s", pid, "; ".join(errs))

        logger.info("discovery: %d modules imported, %d plugins valid", imported, len(valid))

    @staticmethod
    def _import_module(module_name: str, file_path: Path) -> None:
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if not spec or not spec.loader:
            raise ImportError(f"cannot build spec for {module_name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    # ---------------------------------------------------------------- registry

    def register_plugin(self, plugin_cls: Type[BasePlugin]) -> Type[BasePlugin]:
        self._plugins[plugin_cls.manifest.id] = plugin_cls
        return plugin_cls

    def get(self, plugin_id: str) -> Optional[Type[BasePlugin]]:
        return self._plugins.get(plugin_id)

    def get_all_manifests(self) -> List[dict]:
        out: List[dict] = []
        for pid, cls in self._plugins.items():
            try:
                m = cls.manifest.model_dump()
                m["tool_count"] = len(cls.manifest.tools)
                out.append(m)
            except Exception as exc:
                logger.error("manifest extraction failed for %s: %s", pid, exc)
        out.sort(key=lambda m: (m.get("category", ""), m.get("name", "")))
        return out

    async def validate_all_plugins(self) -> Dict[str, dict]:
        return await self.validator.validate_all_discovered_plugins(self._plugins)


registry_instance = PluginRegistry()
PLUGIN_REGISTRY = registry_instance._plugins


def register_plugin(plugin_cls: Type[BasePlugin]) -> Type[BasePlugin]:
    """Decorator used by every module inside plugins_catalog."""
    return registry_instance.register_plugin(plugin_cls)


async def get_plugin_from_registry(plugin_id: str) -> Optional[Type[BasePlugin]]:
    return registry_instance.get(plugin_id)
