"""Plugin & integration marketplace registry."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

PLUGINS: Dict[str, dict] = {}


def register(manifest: dict) -> dict:
    pid = manifest.get("id") or uuid.uuid4().hex[:12]
    p = {"id": pid, "name": manifest.get("name", pid),
         "version": manifest.get("version", "1.0.0"),
         "description": manifest.get("description", ""),
         "author": manifest.get("author", ""),
         "permissions": manifest.get("permissions", []),
         "enabled": False, "installed_at": time.time(),
         "config": manifest.get("config", {}), "entrypoint": manifest.get("entrypoint", "")}
    PLUGINS[pid] = p
    return p


def get(pid: str) -> Optional[dict]:
    return PLUGINS.get(pid)


def list_all() -> List[dict]:
    return list(PLUGINS.values())


def enable(pid: str) -> bool:
    p = PLUGINS.get(pid)
    if not p:
        return False
    p["enabled"] = True
    return True


def disable(pid: str) -> bool:
    p = PLUGINS.get(pid)
    if not p:
        return False
    p["enabled"] = False
    return True


def uninstall(pid: str) -> bool:
    return PLUGINS.pop(pid, None) is not None


def update_config(pid: str, config: dict) -> Optional[dict]:
    p = PLUGINS.get(pid)
    if not p:
        return None
    p["config"].update(config)
    return p
