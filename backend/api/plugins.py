from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.plugins.deps import get_manager, get_store, get_runtime
from backend.plugins.registry import registry_instance

router = APIRouter()


# --------------------------------------------------------------------- schemas

class AuthPayload(BaseModel):
    credentials: Dict[str, Any] = Field(default_factory=dict)


class TestPayload(BaseModel):
    credentials: Optional[Dict[str, Any]] = None


def _user(x_user_id: Optional[str]) -> str:
    # Multi-user hook — replace with your real auth dependency.
    return x_user_id or "default_user"


# ---------------------------------------------------------------------- routes

@router.get("/plugins")
async def list_available_plugins(x_user_id: Optional[str] = Header(None)):
    """Full catalog of discovered + validated plugins, with install state merged in."""
    manager = get_manager()
    user = _user(x_user_id)

    catalog = manager.list_available_plugins()
    installs = {p["id"]: p for p in await manager.get_installed_plugins(user)}

    for manifest in catalog:
        installed = installs.get(manifest["id"])
        manifest["is_installed"] = bool(installed)
        manifest["is_enabled"] = bool(installed and installed.get("is_enabled"))

    return catalog


@router.get("/plugins/installed")
async def get_installed_plugins(x_user_id: Optional[str] = Header(None)):
    return await get_manager().get_installed_plugins(_user(x_user_id))


@router.get("/plugins/status")
async def plugin_system_status():
    store = get_store()
    return {
        "registered_plugins": len(registry_instance._plugins),
        "loaded": len(registry_instance._plugins) > 0,
        "audit_entries": store.snapshot()["usage_log_size"],
    }


@router.get("/plugins/{plugin_id}")
async def get_plugin_detail(plugin_id: str, x_user_id: Optional[str] = Header(None)):
    manager = get_manager()
    user = _user(x_user_id)

    for manifest in manager.list_available_plugins():
        if manifest["id"] == plugin_id:
            installed = next(
                (p for p in await manager.get_installed_plugins(user) if p["id"] == plugin_id),
                None,
            )
            manifest["is_installed"] = bool(installed)
            manifest["is_enabled"] = bool(installed and installed.get("is_enabled"))
            return manifest

    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")


@router.post("/plugins/install/{plugin_id}")
async def install_plugin(plugin_id: str, x_user_id: Optional[str] = Header(None)):
    ok = await get_manager().install_plugin(_user(x_user_id), plugin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Install failed — plugin not registered")
    return {"status": "installed", "plugin_id": plugin_id}


@router.post("/plugins/auth/{plugin_id}")
async def authenticate_plugin(
    plugin_id: str, payload: AuthPayload, x_user_id: Optional[str] = Header(None)
):
    if not payload.credentials:
        raise HTTPException(status_code=422, detail="No credentials supplied")

    ok = await get_manager().authenticate_plugin(_user(x_user_id), plugin_id, payload.credentials)
    if not ok:
        raise HTTPException(status_code=400, detail="Credential validation failed")
    return {"status": "authenticated", "plugin_id": plugin_id}


@router.post("/plugins/test/{plugin_id}")
async def test_plugin_connection(
    plugin_id: str, payload: TestPayload, x_user_id: Optional[str] = Header(None)
):
    result = await get_manager().test_connection(
        _user(x_user_id), plugin_id, payload.credentials
    )
    return result


@router.post("/plugins/toggle/{plugin_id}")
async def toggle_plugin(plugin_id: str, enable: bool, x_user_id: Optional[str] = Header(None)):
    manager = get_manager()
    user = _user(x_user_id)
    ok = await manager.enable_plugin(user, plugin_id) if enable else await manager.disable_plugin(
        user, plugin_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    return {"status": "enabled" if enable else "disabled", "plugin_id": plugin_id}


@router.delete("/plugins/uninstall/{plugin_id}")
async def uninstall_plugin(plugin_id: str, x_user_id: Optional[str] = Header(None)):
    ok = await get_manager().uninstall_plugin(_user(x_user_id), plugin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    return {"status": "uninstalled", "plugin_id": plugin_id}


@router.get("/plugins/tools/active")
async def get_active_tools(x_user_id: Optional[str] = Header(None)):
    """All tools the agent currently has access to, for the chat tool badge."""
    return await get_runtime().get_user_tools(_user(x_user_id))
