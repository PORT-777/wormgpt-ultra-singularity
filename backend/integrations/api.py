"""
FastAPI router for the OAuth 2.0 / OIDC account-linking system.

Public surface (all under /api/integrations):

  GET    ""                          merged catalog + live connection state
  GET    "/providers"                provider descriptors (no secrets)
  GET    "/callback"                 provider redirect target
  GET    "/{plugin_id}"              one integration
  GET    "/{plugin_id}/connect"      browser redirect into the provider
  POST   "/{plugin_id}/connect"      JSON authorization URL (popup clients)
  GET    "/{plugin_id}/status"       sanitized connection status
  GET    "/{plugin_id}/permissions"  scopes + account (no tokens)
  POST   "/{plugin_id}/refresh"      force a token refresh
  POST   "/{plugin_id}/disconnect"   revoke + delete
  POST   "/{plugin_id}/test"         live connection probe
"""

from __future__ import annotations

import html
import json
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from integrations.deps import (
    ensure_registry_discovered,
    get_integration_store,
    get_oauth_service,
)
from integrations.providers import no_oauth_reason, provider_catalog
from integrations.service import (
    OAuthNotSupported,
    ProviderNotConfigured,
    safe_return_to,
)
from integrations.store import connection_health
from plugins_system.deps import get_manager
from plugins_system.registry import registry_instance

log = logging.getLogger("integrations_api")

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# --------------------------------------------------------------------- models

class ConnectRequest(BaseModel):
    user_id: str = "default_user"
    return_to: str = "/"
    popup: bool = True


class ActionRequest(BaseModel):
    user_id: str = "default_user"
    revoke: bool = True


# -------------------------------------------------------------------- helpers

def _redirect_uri(request: Request) -> str:
    explicit = (os.getenv("OAUTH_REDIRECT_URI") or "").strip()
    if explicit:
        return explicit
    return str(request.base_url).rstrip("/") + "/api/integrations/callback"


def _append(return_to: str, params: Dict[str, Any]) -> str:
    base = safe_return_to(return_to)
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    if not clean:
        return base
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{urlencode(clean)}"


def _popup_html(payload: Dict[str, Any], title: str) -> str:
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#0A0A0A; color:#F5F5F5; font-family:system-ui,-apple-system,Segoe UI,sans-serif; }}
  .box {{ text-align:center; padding:28px 30px; border:1px solid #2a2a2a; border-radius:14px;
          background:#111; max-width:340px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; background:#CC0000; margin:0 auto 14px;
          animation:pulse 1.1s ease-in-out infinite; }}
  @keyframes pulse {{ 0%,100%{{opacity:.35;transform:scale(.9)}} 50%{{opacity:1;transform:scale(1.15)}} }}
  p {{ margin:8px 0 0; font-size:13px; color:#b9b9b9; line-height:1.5; }}
</style>
</head>
<body>
  <div class="box">
    <div class="dot"></div>
    <strong style="font-size:14px">{html.escape(title)}</strong>
    <p>Your project is linked. You can close this tab.</p>
  </div>
<script>
(function () {{
  var payload = {safe_payload};
  try {{
    if (window.opener) {{
      window.opener.postMessage(payload, window.location.origin);
    }}
  }} catch (e) {{}}
  setTimeout(function () {{ try {{ window.close(); }} catch (e) {{}} }}, 350);
}})();
</script>
</body>
</html>"""


def _error_response(
    *,
    plugin_id: str,
    return_to: str,
    reason: str,
    detail: str,
    popup: bool,
) -> Any:
    if popup:
        return HTMLResponse(
            _popup_html(
                {
                    "type": "wormgpt-integration",
                    "status": "error",
                    "plugin": plugin_id,
                    "reason": reason,
                    "detail": detail[:300],
                },
                "Authorization failed",
            ),
            status_code=400,
        )
    return RedirectResponse(
        _append(
            return_to,
            {
                "integration": "error",
                "plugin": plugin_id,
                "reason": reason,
                "detail": detail[:300],
            },
        ),
        status_code=302,
    )


async def _plugin_item(user_id: str, user_plugins: Dict[str, Any], connections: Dict[str, Any], manifest: Dict[str, Any]) -> Dict[str, Any]:
    from integrations.providers import get_provider

    plugin_id = manifest["id"]
    spec = get_provider(plugin_id)
    record = user_plugins.get(plugin_id)
    connection = connections.get(plugin_id)

    if spec is None:
        if manifest.get("auth_type") == "none":
            status = "no_auth_required"
        else:
            status = "unsupported"
        return {
            **manifest,
            "is_installed": bool(record),
            "is_enabled": bool(record and record.is_enabled),
            "oauth_supported": False,
            "oauth_reason": None if status == "no_auth_required" else no_oauth_reason(plugin_id),
            "oauth": None,
            "status": status,
            "connection": None,
            "account": None,
            "scopes": [],
            "setup_required": False,
        }

    if connection is not None:
        if connection.status == "connected" and connection.is_expired(0):
            status = "connection_expired"
        elif connection.status == "expired":
            status = "connection_expired"
        else:
            status = connection.status
    elif not spec.is_configured():
        status = "setup_required"
    else:
        status = "not_connected"

    return {
        **manifest,
        "is_installed": bool(record),
        "is_enabled": bool(record and record.is_enabled),
        "oauth_supported": True,
        "oauth_reason": None,
        "oauth": spec.public(),
        "status": status,
        "setup_required": not spec.is_configured(),
        "connection": connection.public() if connection else None,
        "account": (
            connection.account_name or connection.account_email or connection.account_id
        )
        if connection
        else None,
        "account_email": connection.account_email if connection else None,
        "scopes": list(connection.scopes) if connection and connection.scopes else list(spec.scopes),
        "expires_at": connection.expires_at if connection else None,
        "connected_at": connection.created_at if connection else None,
        "health": connection_health(connection, spec) if connection else None,
    }


# --------------------------------------------------------------------- routes

@router.get("")
async def list_integrations(user_id: str = "default_user"):
    await ensure_registry_discovered()
    manager = get_manager()
    store = get_integration_store()

    manifests = registry_instance.get_all_manifests()
    records = await manager.db.get_user_plugins(user_id, enabled_only=False)
    user_plugins = {r.plugin_id: r for r in records}
    connections = {c.plugin_id: c for c in await store.list_for_user(user_id)}

    items = [
        await _plugin_item(user_id, user_plugins, connections, m) for m in manifests
    ]
    counts = {
        "total": len(items),
        "oauth_supported": sum(1 for i in items if i.get("oauth_supported")),
        "configured": sum(
            1 for i in items if i.get("oauth_supported") and (i.get("oauth") or {}).get("configured")
        ),
        "connected": sum(1 for i in items if i.get("status") == "connected"),
        "expired": sum(1 for i in items if i.get("status") == "connection_expired"),
        "installed": sum(1 for i in items if i.get("is_installed")),
        "expiring": sum(
            1 for i in items if (i.get("health") or {}).get("expiring_soon")
        ),
        "needs_attention": sum(
            1
            for i in items
            if i.get("status") == "connection_expired"
            or (i.get("health") or {}).get("needs_reconnect")
        ),
        "setup_required": sum(1 for i in items if i.get("status") == "setup_required"),
    }
    return {
        "user_id": user_id,
        "integrations": items,
        "counts": counts,
        "providers": provider_catalog(),
    }


@router.get("/providers")
async def list_providers():
    return {"providers": provider_catalog()}


@router.get("/health")
async def integration_health(
    user_id: str = "default_user",
    refresh: bool = False,
    window: int = Query(default=900, ge=60, le=86400),
):
    """Aggregated health for every linked account.

    ``refresh=true`` proactively renews tokens that expire inside ``window``
    seconds, which is what the UI uses for automatic reconnection.
    """
    from integrations.providers import get_provider

    service = get_oauth_service()
    store = get_integration_store()
    connections = await store.list_for_user(user_id)

    accounts: List[Dict[str, Any]] = []
    renewed: List[str] = []
    refresh_errors: List[Dict[str, str]] = []

    for connection in connections:
        spec = get_provider(connection.plugin_id)
        should_refresh = bool(
            refresh
            and connection.status == "connected"
            and connection.is_expired(window)
            and spec is not None
            and spec.refresh
            and connection.refresh_token
        )
        if should_refresh:
            try:
                await service.ensure_fresh(
                    user_id, connection.plugin_id, skew_seconds=window
                )
                renewed.append(connection.plugin_id)
            except Exception as exc:  # noqa: BLE001
                refresh_errors.append(
                    {"plugin_id": connection.plugin_id, "error": str(exc)[:200]}
                )
            connection = store.get_sync(user_id, connection.plugin_id) or connection

        health = connection_health(connection, spec)
        accounts.append(
            {
                "plugin_id": connection.plugin_id,
                "provider": {
                    "name": spec.name if spec else connection.plugin_id,
                    "icon": spec.icon if spec else "🔌",
                },
                "account": connection.account_name
                or connection.account_email
                or connection.account_id,
                "account_email": connection.account_email,
                **health,
            }
        )

    summary = {
        "connections": len(accounts),
        "healthy": sum(1 for a in accounts if a["healthy"]),
        "expiring_soon": sum(1 for a in accounts if a["expiring_soon"]),
        "expired": sum(1 for a in accounts if a["expired"]),
        "needs_reconnect": sum(1 for a in accounts if a["needs_reconnect"]),
        "auto_refreshable": sum(1 for a in accounts if a["auto_refresh"]),
    }
    return {
        "user_id": user_id,
        "summary": summary,
        "accounts": accounts,
        "renewed": renewed,
        "refresh_errors": refresh_errors,
    }


@router.post("/refresh-all")
async def refresh_all(
    user_id: str = "default_user",
    window: int = Query(default=900, ge=60, le=86400),
):
    """Renew every connection that expires inside ``window`` seconds."""
    return await integration_health(user_id=user_id, refresh=True, window=window)


@router.get("/history")
async def integration_history(
    user_id: str = "default_user",
    plugin_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Sanitized audit trail (connect, refresh, failure, disconnect)."""
    rows = get_integration_store().history(
        user_id, plugin_id=plugin_id, limit=limit
    )
    return {"user_id": user_id, "plugin_id": plugin_id, "events": rows, "count": len(rows)}


# NOTE: /callback must be declared before /{plugin_id} so it is not captured.
@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
):
    service = get_oauth_service()
    outcome = await service.handle_callback(
        state=state,
        code=code,
        error=error,
        error_description=error_description,
    )

    if outcome.ok:
        if outcome.popup:
            return HTMLResponse(
                _popup_html(
                    {
                        "type": "wormgpt-integration",
                        "status": "connected",
                        "plugin": outcome.plugin_id,
                        "account": outcome.account_name,
                    },
                    "Connected to your project — تم الربط بمشروعك",
                )
            )
        return RedirectResponse(
            _append(
                outcome.return_to,
                {
                    "integration": "connected",
                    "plugin": outcome.plugin_id,
                    "account": outcome.account_name,
                },
            ),
            status_code=302,
        )

    if outcome.popup:
        return HTMLResponse(
            _popup_html(
                {
                    "type": "wormgpt-integration",
                    "status": "error",
                    "plugin": outcome.plugin_id,
                    "reason": outcome.error_code or "authorization_failed",
                    "detail": outcome.error_detail,
                },
                "Authorization failed",
            ),
            status_code=400,
        )
    return RedirectResponse(
        _append(
            outcome.return_to,
            {
                "integration": "error",
                "plugin": outcome.plugin_id,
                "reason": outcome.error_code or "authorization_failed",
                "detail": outcome.error_detail,
            },
        ),
        status_code=302,
    )


@router.get("/{plugin_id}")
async def get_integration(plugin_id: str, user_id: str = "default_user"):
    await ensure_registry_discovered()
    manifest = next(
        (m for m in registry_instance.get_all_manifests() if m["id"] == plugin_id), None
    )
    if not manifest:
        raise HTTPException(404, f"Unknown integration '{plugin_id}'")
    manager = get_manager()
    records = await manager.db.get_user_plugins(user_id, enabled_only=False)
    connections = {
        c.plugin_id: c for c in await get_integration_store().list_for_user(user_id)
    }
    return await _plugin_item(
        user_id,
        {r.plugin_id: r for r in records},
        connections,
        manifest,
    )


@router.get("/{plugin_id}/connect")
async def connect_browser(
    request: Request,
    plugin_id: str,
    user_id: str = "default_user",
    return_to: str = "/",
    popup: bool = False,
    as_json: bool = False,
):
    service = get_oauth_service()
    try:
        result = await service.create_authorization(
            user_id=user_id,
            plugin_id=plugin_id,
            redirect_uri=_redirect_uri(request),
            return_to=return_to,
            popup=popup,
        )
    except OAuthNotSupported as exc:
        if as_json:
            raise HTTPException(400, str(exc)) from exc
        return _error_response(
            plugin_id=plugin_id,
            return_to=return_to,
            reason=exc.code,
            detail=str(exc),
            popup=popup,
        )
    except ProviderNotConfigured as exc:
        if as_json:
            raise HTTPException(409, str(exc)) from exc
        return _error_response(
            plugin_id=plugin_id,
            return_to=return_to,
            reason=exc.code,
            detail=str(exc),
            popup=popup,
        )
    except Exception as exc:
        log.exception("connect failed for %s", plugin_id)
        if as_json:
            raise HTTPException(500, "Could not start authorization") from exc
        return _error_response(
            plugin_id=plugin_id,
            return_to=return_to,
            reason="authorization_failed",
            detail=f"{type(exc).__name__}: {exc}",
            popup=popup,
        )

    if as_json:
        return result
    return RedirectResponse(result["authorization_url"], status_code=302)


@router.post("/{plugin_id}/connect")
async def connect_json(request: Request, plugin_id: str, req: ConnectRequest):
    service = get_oauth_service()
    try:
        return await service.create_authorization(
            user_id=req.user_id,
            plugin_id=plugin_id,
            redirect_uri=_redirect_uri(request),
            return_to=req.return_to,
            popup=req.popup,
        )
    except OAuthNotSupported as exc:
        raise HTTPException(400, str(exc)) from exc
    except ProviderNotConfigured as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/{plugin_id}/status")
async def integration_status(plugin_id: str, user_id: str = "default_user"):
    return get_oauth_service().public_status(user_id, plugin_id)


@router.get("/{plugin_id}/permissions")
async def integration_permissions(plugin_id: str, user_id: str = "default_user"):
    from integrations.providers import get_provider

    spec = get_provider(plugin_id)
    if not spec:
        raise HTTPException(400, no_oauth_reason(plugin_id))
    connection = get_integration_store().get_sync(user_id, plugin_id)
    return {
        "plugin_id": plugin_id,
        "provider": spec.public(),
        "requested_scopes": list(spec.scopes),
        "granted_scopes": list(connection.scopes) if connection else [],
        "account": connection.public()["account"] if connection else None,
        "status": connection.status if connection else "not_connected",
        "docs_url": spec.docs_url,
        "revocation_supported": bool(spec.revocation_endpoint),
        "notes": spec.notes,
    }


@router.post("/{plugin_id}/refresh")
async def refresh_integration(plugin_id: str, req: Optional[ActionRequest] = None):
    user_id = (req.user_id if req else None) or "default_user"
    try:
        connection = await get_oauth_service().refresh(user_id, plugin_id, force=True)
        return {"ok": True, "status": connection.public()}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{plugin_id}/disconnect")
async def disconnect_integration(plugin_id: str, req: Optional[ActionRequest] = None):
    user_id = (req.user_id if req else None) or "default_user"
    revoke = req.revoke if req else True
    service = get_oauth_service()
    if not revoke:
        # Still delete locally; the caller explicitly asked not to call provider.
        store = get_integration_store()
        connection = store.get_sync(user_id, plugin_id)
        deleted = await store.delete(user_id, plugin_id)
        try:
            await get_manager().disable_plugin(user_id, plugin_id)
        except Exception:
            pass
        await store.record_event(
            user_id,
            plugin_id,
            "disconnect",
            status="warn",
            account=(connection.account_name or connection.account_email) if connection else None,
            detail="Deleted locally at the user's request; provider revocation was skipped.",
        )
        return {"ok": True, "revoked": False, "deleted": deleted, "had_connection": bool(connection)}
    return await service.disconnect(user_id, plugin_id)


@router.delete("/{plugin_id}")
async def disconnect_integration_delete(plugin_id: str, user_id: str = "default_user"):
    return await get_oauth_service().disconnect(user_id, plugin_id)


@router.post("/{plugin_id}/test")
async def test_integration(plugin_id: str, req: Optional[ActionRequest] = None):
    user_id = (req.user_id if req else None) or "default_user"
    service = get_oauth_service()
    await service.ensure_fresh(user_id, plugin_id)
    manager = get_manager()
    result = await manager.test_connection(user_id, plugin_id)
    ok = result.get("status") in {"ok", "success", "connected"}
    await service.audit(
        user_id,
        plugin_id,
        "test",
        status="ok" if ok else "error",
        detail=str(result.get("message") or "")[:200],
    )
    return {
        "plugin_id": plugin_id,
        "status": result.get("status", "error"),
        "message": result.get("message", ""),
        "details": {k: v for k, v in result.items() if k not in {"status", "message"}},
    }
