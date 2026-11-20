"""
Plugin API Router - FastAPI routes for the plugin system.
Mounts into main.py via app.include_router.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from plugins_system.deps import get_manager, get_runtime, get_store
from plugins_system.registry import registry_instance
from plugins_system.broker import PluginBroker

log = logging.getLogger("plugins_api")

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# Lazy-initialized broker for direct tool execution
_broker: Optional[PluginBroker] = None


def get_broker() -> PluginBroker:
    global _broker
    if _broker is None:
        _broker = PluginBroker()
    return _broker


# ----------------------------------------------------------------- models ----

class InstallRequest(BaseModel):
    plugin_id: str


class AuthRequest(BaseModel):
    credentials: Dict[str, Any] = Field(default_factory=dict)


class TestRequest(BaseModel):
    credentials: Optional[Dict[str, Any]] = None


class ExecuteRequest(BaseModel):
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"


# ------------------------------------------------------------------- routes ----

@router.get("")
async def list_plugins(
    category: Optional[str] = None,
    q: Optional[str] = None,
):
    """List all available plugins (catalog)."""
    manifests = registry_instance.get_all_manifests()
    result: List[Dict[str, Any]] = []
    for m in manifests:
        if category and m.get("category") != category:
            continue
        if q:
            needle = q.lower()
            haystack = f"{m['name']} {m['id']} {m.get('description','')} {' '.join(m.get('tags',[]))}".lower()
            if needle not in haystack:
                continue
        result.append(m)
    return result


@router.get("/installed")
async def list_installed(user_id: str = "default_user"):
    """List plugins installed for a user."""
    manager = get_manager()
    return await manager.get_installed_plugins(user_id)


@router.get("/status")
async def plugin_status():
    """System-level plugin status."""
    manifests = registry_instance.get_all_manifests()
    return {
        "total": len(manifests),
        "categories": len(set(m.get("category","") for m in manifests)),
        "tools": sum(len(m.get("tools",[])) for m in manifests),
        "audit_entries": 0,
    }


@router.get("/audit/summary")
async def audit_summary():
    """Audit summary for the UI."""
    store = get_store()
    try:
        snap = store.snapshot()
        return {
            "total_calls": snap.get("usage_log_size", 0),
            "failures": 0,
            "security_alerts": snap.get("security_alerts", 0),
            "by_plugin": {},
        }
    except Exception:
        return {"total_calls": 0, "failures": 0, "security_alerts": 0, "by_plugin": {}}


@router.post("/install/{plugin_id}")
async def install_plugin(plugin_id: str, user_id: str = "default_user"):
    """Install a plugin for a user."""
    manager = get_manager()
    ok = await manager.install_plugin(user_id, plugin_id)
    if not ok:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")
    return {"ok": True, "plugin_id": plugin_id, "installed": True}


@router.post("/uninstall/{plugin_id}")
async def uninstall_plugin(plugin_id: str, user_id: str = "default_user"):
    """Uninstall a plugin and wipe its credentials."""
    manager = get_manager()
    ok = await manager.uninstall_plugin(user_id, plugin_id)
    return {"ok": ok, "plugin_id": plugin_id}


@router.post("/toggle/{plugin_id}")
async def toggle_plugin(plugin_id: str, enable: bool = True, user_id: str = "default_user"):
    """Enable or disable a plugin for a user."""
    manager = get_manager()
    if enable:
        ok = await manager.enable_plugin(user_id, plugin_id)
    else:
        ok = await manager.disable_plugin(user_id, plugin_id)
    return {"ok": ok, "plugin_id": plugin_id, "enabled": enable}


@router.post("/auth/{plugin_id}")
async def authenticate_plugin(plugin_id: str, req: AuthRequest, user_id: str = "default_user"):
    """Validate and store credentials for a plugin."""
    manager = get_manager()
    ok = await manager.authenticate_plugin(user_id, plugin_id, req.credentials)
    if not ok:
        raise HTTPException(400, "credential validation failed")
    return {"ok": True, "plugin_id": plugin_id}


@router.post("/test/{plugin_id}")
async def test_connection(plugin_id: str, req: Optional[TestRequest] = None, user_id: str = "default_user"):
    """Test a plugin's connection."""
    manager = get_manager()
    creds = req.credentials if req else None
    result = await manager.test_connection(user_id, plugin_id, creds)
    return result


@router.post("/execute")
async def execute_tool(req: ExecuteRequest):
    """Execute a plugin tool directly (for testing)."""
    broker = get_broker()
    try:
        result = await broker.execute(req.tool, req.args, user_id=req.user_id)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.get("/catalog")
async def catalog():
    """Full plugin catalog with tool definitions."""
    broker = get_broker()
    return {
        "plugins": registry_instance.get_all_manifests(),
        "tools": broker.get_all_tool_definitions(),
    }