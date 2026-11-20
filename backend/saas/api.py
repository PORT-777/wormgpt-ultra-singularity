"""HTTP API for accounts, billing, entitlements and admin."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response

try:
    from .. import database, storage_backends
except ImportError:  # imported as top-level `saas` package in tests
    import database
    import storage_backends

from . import api_keys as keys
from . import auth, db, files, payments, platform, plans, usage

router = APIRouter(prefix="/api/saas", tags=["saas"])


def _bearer(authorization: Optional[str]) -> str:
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    return parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else ""


def _user(authorization: Optional[str]) -> Dict[str, Any]:
    u = auth.user_from_token(_bearer(authorization))
    if not u:
        raise HTTPException(401, "authentication required")
    return u


def _admin(u: Dict[str, Any]) -> None:
    if u.get("role") != "admin":
        raise HTTPException(403, "admin access required")


@router.get("/plans")
async def get_plans():
    return {"plans": plans.list_plans()}


@router.post("/auth/register")
async def register(payload: dict = Body(...)):
    try:
        return auth.register(str(payload.get("email") or ""), str(payload.get("password") or ""),
                             str(payload.get("username") or ""))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/auth/verify")
async def verify(payload: dict = Body(...)):
    if not auth.verify_email(str(payload.get("token") or "")):
        raise HTTPException(400, "invalid or expired token")
    return {"ok": True}


@router.post("/auth/login")
async def login(payload: dict = Body(...), request: Request = None):
    try:
        return auth.login(
            str(payload.get("email") or ""), str(payload.get("password") or ""),
            remember=bool(payload.get("remember")),
            ip=(request.client.host if request and request.client else ""),
            user_agent=(request.headers.get("user-agent", "") if request else ""),
        )
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc


@router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    return {"ok": auth.logout(_bearer(authorization))}


@router.post("/auth/request-reset")
async def request_reset(payload: dict = Body(...)):
    return auth.request_password_reset(str(payload.get("email") or ""))


@router.post("/auth/reset")
async def reset(payload: dict = Body(...)):
    try:
        return {"ok": auth.reset_password(str(payload.get("token") or ""), str(payload.get("password") or ""))}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/me")
async def me(authorization: Optional[str] = Header(None)):
    return {"user": _user(authorization)}


@router.post("/me/password")
async def change_password(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    u = _user(authorization)
    try:
        return {"ok": auth.change_password(u["id"], str(payload.get("old") or ""), str(payload.get("new") or ""))}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/me/sessions")
async def sessions(authorization: Optional[str] = Header(None)):
    return {"sessions": auth.list_sessions(_user(authorization)["id"])}


@router.delete("/me")
async def delete_me(authorization: Optional[str] = Header(None)):
    return {"ok": auth.delete_account(_user(authorization)["id"])}


@router.get("/entitlements")
async def entitlements(authorization: Optional[str] = Header(None)):
    return usage.entitlement(_user(authorization)["id"])


@router.get("/usage")
async def get_usage(authorization: Optional[str] = Header(None)):
    return usage.usage_summary(_user(authorization)["id"])


@router.get("/subscription")
async def subscription(authorization: Optional[str] = Header(None)):
    return plans.ensure_subscription(_user(authorization)["id"])


@router.post("/checkout")
async def checkout(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    u = _user(authorization)
    try:
        return payments.create_checkout(u["id"], str(payload.get("plan_id") or ""),
                                        str(payload.get("period") or "monthly"))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/webhook/paymob")
async def paymob_webhook(payload: dict = Body(...), hmac_value: Optional[str] = Header(None, alias="hmac")):
    valid = payments.verify_hmac(payload, hmac_value or "")
    platform.record_webhook("paymob", "transaction", payload, valid)
    if not valid:
        raise HTTPException(400, "invalid Paymob HMAC signature")
    try:
        result = payments.handle_callback(payload, hmac_value or "")
        platform.audit("webhook", "paymob_callback", str(result.get("payment_id") or ""),
                       {"duplicate": result.get("duplicate", False)})
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/payments")
async def payment_history(page: int = 1, limit: int = 50,
                          authorization: Optional[str] = Header(None)):
    p, size, offset = database.page_params(page, limit)
    c = db.conn()
    rows = c.execute(
        "SELECT id,plan_id,provider,amount,currency,status,event,created FROM saas_payments "
        "WHERE user_id=? ORDER BY created DESC LIMIT ? OFFSET ?",
        (_user(authorization)["id"], size, offset),
    ).fetchall()
    return {"payments": [dict(r) for r in rows], "page": p, "limit": size}


@router.get("/api-keys")
async def list_api_keys(authorization: Optional[str] = Header(None)):
    return {"keys": keys.list_keys(_user(authorization)["id"])}


@router.post("/api-keys")
async def create_api_key(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    return keys.create(_user(authorization)["id"], str(payload.get("name") or ""),
                       payload.get("permissions"))


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, authorization: Optional[str] = Header(None)):
    return {"ok": keys.revoke(_user(authorization)["id"], key_id)}


@router.get("/payment-status")
async def payment_status():
    return payments.status()


@router.get("/me/profile")
async def get_profile(authorization: Optional[str] = Header(None)):
    return {"profile": platform.get_profile(_user(authorization)["id"])}


@router.put("/me/profile")
async def put_profile(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    u = _user(authorization)
    result = platform.upsert_profile(u["id"], payload)
    platform.audit(u["id"], "profile_update", u["id"])
    return {"profile": result}


@router.get("/me/credits")
async def get_credits(authorization: Optional[str] = Header(None)):
    uid = _user(authorization)["id"]
    return {"balance": platform.credit_balance(uid),
            "history": platform.credit_history(uid)}


# --- files / object storage ---
@router.get("/storage/status")
async def storage_status():
    return storage_backends.storage_status()


@router.get("/files")
async def list_files(bucket: str = "", page: int = 1, limit: int = 50,
                     authorization: Optional[str] = Header(None)):
    return files.list_files(_user(authorization)["id"], bucket, page, limit)


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), bucket: str = Form("user-files"),
                      authorization: Optional[str] = Header(None)):
    u = _user(authorization)
    data = await file.read()
    try:
        row = files.upload(u["id"], bucket, file.filename or "file", data,
                           file.content_type or "")
    except (ValueError, storage_backends.StorageError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    usage.record(u["id"], "storage_bytes", len(data), session_id=row["id"])
    return row


@router.get("/files/object")
async def signed_object(bucket: str, path: str, expires: int, sig: str):
    try:
        data = files.object_from_signature(bucket, path, expires, sig)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(content=data, media_type="application/octet-stream")


@router.get("/files/{file_id}")
async def get_file(file_id: str, authorization: Optional[str] = Header(None)):
    try:
        return files.get(file_id, _user(authorization)["id"])
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/files/{file_id}/url")
async def file_url(file_id: str, expires: int = 3600,
                   authorization: Optional[str] = Header(None)):
    try:
        return {"url": files.signed_url(_user(authorization)["id"], file_id, expires)}
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/files/{file_id}/content")
async def file_content(file_id: str, authorization: Optional[str] = Header(None)):
    u = _user(authorization)
    try:
        row = files.get(file_id, u["id"])
        data = files.download(u["id"], file_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(content=data, media_type=row.get("content_type") or "application/octet-stream")


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, authorization: Optional[str] = Header(None)):
    try:
        return {"ok": files.delete(_user(authorization)["id"], file_id)}
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


# --- admin ---
@router.get("/admin/users")
async def admin_users(page: int = 1, limit: int = 50,
                      authorization: Optional[str] = Header(None)):
    _admin(_user(authorization))
    p, size, offset = database.page_params(page, limit)
    c = db.conn()
    total = c.execute("SELECT COUNT(*) FROM saas_users").fetchone()[0]
    rows = c.execute(
        "SELECT id,email,username,role,status,email_verified,created FROM saas_users "
        "ORDER BY created DESC LIMIT ? OFFSET ?", (size, offset),
    ).fetchall()
    return {"users": [dict(r) for r in rows], "total": int(total),
            "page": p, "limit": size}


@router.post("/admin/plans/{plan_id}")
async def admin_upsert_plan(plan_id: str, payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    _admin(_user(authorization))
    return plans.upsert_plan(plan_id, payload)


@router.get("/admin/payments")
async def admin_payments(authorization: Optional[str] = Header(None)):
    _admin(_user(authorization))
    c = db.conn()
    rows = c.execute("SELECT * FROM saas_payments ORDER BY created DESC LIMIT 500").fetchall()
    return {"payments": [dict(r) for r in rows]}


@router.get("/admin/audit")
async def admin_audit(page: int = 1, limit: int = 50,
                      authorization: Optional[str] = Header(None)):
    u = _user(authorization)
    _admin(u)
    result = platform.audit_events(page, limit)
    platform.audit(u["id"], "audit_view", "admin")
    return result
