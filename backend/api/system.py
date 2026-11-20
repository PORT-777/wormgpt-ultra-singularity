"""System endpoints consumed by the React UI on boot.

These routes lived in the pre-split main.py and were lost when the entrypoint
was replaced. They are grouped here so the connection pill, history, gamification,
checkpoints and runtime panels work again.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_UPLOAD_DIR = _BACKEND_DIR / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(tags=["system"])


def _safe(module: str, name: str = ""):
    import importlib

    try:
        mod = importlib.import_module(module)
        return getattr(mod, name) if name else mod
    except Exception:
        return None


storage = _safe("storage")
gamification = _safe("gamification")
checkpoint = _safe("checkpoint")
runtime_env = _safe("runtime_env")
memory_store = _safe("memory.store")
file_workspace = _safe("file_workspace")
prompt_library = _safe("prompt_library")
proposals = _safe("proposals")
execution = _safe("execution")
voice = _safe("voice")

if storage is not None and hasattr(storage, "init"):
    try:
        storage.init()
    except Exception:
        pass


def _ok(value: Any, fallback: Any) -> Any:
    return value if value is not None else fallback


# --- connection + version ----------------------------------------------
@router.get("/api/status")
async def api_status():
    plugins_loaded = 0
    try:
        from plugins_system.registry import registry_instance

        plugins_loaded = len(registry_instance._plugins)
    except Exception:
        pass
    return {
        "state": "ready",
        "route": "auto",
        "providers": {},
        "auth_required": bool(os.getenv("ADMIN_PASSWORD", "").strip()),
        "plugins_loaded": plugins_loaded,
        "version": "6.1.0",
    }


@router.get("/api/version")
async def api_version():
    return {"version": "6.1.0", "build": "6.1.0", "asset": "6.1.0"}


@router.get("/api/runtime")
async def api_runtime():
    summary = runtime_env.summary() if runtime_env and hasattr(runtime_env, "summary") else None
    environments = (
        runtime_env.available_environments()
        if runtime_env and hasattr(runtime_env, "available_environments")
        else []
    )
    return {"summary": summary, "environments": environments}


@router.post("/api/runtime/refresh")
async def api_runtime_refresh():
    if runtime_env and hasattr(runtime_env, "fingerprint"):
        return runtime_env.fingerprint(refresh=True)
    raise HTTPException(503, "runtime_env unavailable")


# --- sessions / history / audit ----------------------------------------
@router.get("/api/history")
async def api_history(q: str = ""):
    return _ok(storage.list_sessions(q) if storage else None, [])


@router.get("/api/sessions")
async def api_sessions(q: str = ""):
    return _ok(storage.list_sessions(q) if storage else None, [])


@router.get("/api/sessions/{session_id}")
async def api_session_get(session_id: str):
    row = storage.get_session(session_id) if storage else None
    if row is None:
        raise HTTPException(404, "session not found")
    return row


@router.delete("/api/sessions/{session_id}")
async def api_session_delete(session_id: str):
    return {"deleted": _ok(storage.delete_session(session_id) if storage else 0, 0)}


@router.get("/api/history/{session_id}")
async def api_session_detail(session_id: str, limit: int = 500):
    row = storage.get_session(session_id) if storage else None
    if row is None:
        raise HTTPException(404, "session not found")
    messages = storage.get_session_messages(session_id, limit=limit) if storage else []
    return {**row, "messages": messages}


@router.get("/api/history/{session_id}/detail")
async def api_session_messages(session_id: str, limit: int = 500):
    return _ok(storage.get_session_messages(session_id, limit=limit) if storage else None, [])


@router.get("/api/history/{session_id}/runs")
async def api_session_runs(session_id: str, limit: int = 2000):
    events = _ok(storage.list_trace_events(session_id, "", limit) if storage else None, [])
    runs: Dict[str, Dict[str, Any]] = {}
    for event in events:
        rid = str(event.get("run_id") or "")
        if rid and rid not in runs:
            runs[rid] = {"run_id": rid, "seq": event.get("seq"), "kind": event.get("kind"), "ts": event.get("ts")}
    return list(runs.values())


@router.get("/api/history/{session_id}/trace")
async def api_session_trace(session_id: str, run_id: str = "", limit: int = 2000):
    return _ok(storage.list_trace_events(session_id, run_id, limit) if storage else None, [])


@router.get("/api/history/{session_id}/export")
async def api_session_export(session_id: str, limit: int = 2000):
    row = storage.get_session_export(session_id, limit) if storage else None
    if row is None:
        raise HTTPException(404, "session not found")
    return row


@router.get("/api/timeline/{session_id}")
async def api_timeline(session_id: str, run_id: str = "", limit: int = 2000):
    return _ok(storage.list_trace_events(session_id, run_id, limit) if storage else None, [])


@router.get("/api/audit")
async def api_audit(limit: int = 100):
    return _ok(storage.get_audit(limit) if storage else None, [])


@router.post("/api/feedback")
async def api_feedback(payload: dict = Body(...)):
    if not storage or not hasattr(storage, "add_feedback"):
        return {"ok": False}
    try:
        fid = storage.add_feedback(
            payload.get("session_id", ""),
            payload.get("message_id", ""),
            int(payload.get("vote", 0)),
        )
        return {"ok": True, "id": fid}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


# --- gamification -------------------------------------------------------
@router.get("/api/gamification/state")
async def api_gamification_state(user_id: str = "default_user"):
    return gamification.state(user_id) if gamification else {}


@router.get("/api/gamification/catalog")
async def api_gamification_catalog():
    return gamification.catalog() if gamification else {}


@router.get("/api/gamification")
async def api_gamification(user_id: str = "default_user"):
    return gamification.state(user_id) if gamification else {}


@router.post("/api/gamification/reset")
async def api_gamification_reset(user_id: str = "default_user"):
    return gamification.reset(user_id) if gamification else {}


# --- checkpoints --------------------------------------------------------
@router.get("/api/checkpoints")
async def api_checkpoints(session_id: str = ""):
    return _ok(checkpoint.list_checkpoints(session_id) if checkpoint else None, [])


@router.post("/api/checkpoints/create")
async def api_checkpoint_create(payload: dict = Body(...)):
    if not checkpoint:
        raise HTTPException(503, "checkpoint unavailable")
    try:
        return checkpoint.create_checkpoint(
            str(payload.get("session_id", "")),
            str(payload.get("message_id", "")),
            list(payload.get("files") or []),
            kind=str(payload.get("kind", "auto")),
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/checkpoints/{checkpoint_id}/diff")
async def api_checkpoint_diff(checkpoint_id: str, session_id: str = ""):
    if not checkpoint:
        raise HTTPException(503, "checkpoint unavailable")
    return {"diff": checkpoint.diff_checkpoint(checkpoint_id, session_id)}


@router.post("/api/checkpoints/{checkpoint_id}/revert")
async def api_checkpoint_revert(checkpoint_id: str, session_id: str = ""):
    if not checkpoint:
        raise HTTPException(503, "checkpoint unavailable")
    return checkpoint.revert_checkpoint(checkpoint_id, session_id)


# --- memory / files / prompts / proposals ------------------------------
@router.get("/api/memory/status")
async def api_memory_status():
    return memory_store.memory_status() if memory_store else {"engine": "unavailable"}


@router.get("/api/memory")
async def api_memory(k: int = 8):
    return _ok(memory_store.recent(k) if memory_store else None, [])


@router.post("/api/memory/index")
async def api_memory_index():
    return {"indexed": _ok(memory_store.index_workspace() if memory_store else 0, 0)}


@router.get("/api/files")
async def api_files(kind: Optional[str] = None, session_id: Optional[str] = None):
    return _ok(file_workspace.list_all(kind, session_id) if file_workspace else None, [])


@router.post("/api/files/upload")
async def api_file_upload(file: UploadFile = File(...)):
    name = Path(file.filename or "upload.bin").name
    dest = _UPLOAD_DIR / name
    data = await file.read()
    dest.write_bytes(data)
    record = None
    if file_workspace:
        try:
            record = file_workspace.register(str(dest), "upload")
        except Exception:
            record = None
    return {"ok": True, "path": str(dest), "size": len(data), "record": record}


@router.get("/api/files/read")
async def api_file_read(path: str):
    target = Path(path)
    base = _BACKEND_DIR.resolve()
    if not target.is_absolute():
        target = base / target
    target = target.resolve()
    if base not in target.parents and target != base:
        raise HTTPException(403, "outside backend directory")
    if not target.is_file():
        raise HTTPException(404, "file not found")
    return {"path": str(target), "content": target.read_text(encoding="utf-8", errors="replace")[:200000]}


@router.get("/api/prompts")
async def api_prompts(q: str = "", tag: Optional[str] = None):
    return _ok(prompt_library.search(q, tag) if prompt_library else None, [])


@router.get("/api/proposals")
async def api_proposals(status: Optional[str] = None):
    return _ok(proposals.list_proposals(status) if proposals else None, [])


# --- exec / sandbox -----------------------------------------------------
@router.get("/api/exec/capabilities")
async def api_exec_capabilities():
    if execution and hasattr(execution, "resolve_environment"):
        return execution.resolve_environment("auto")
    return {"environment": "unknown"}


@router.get("/api/exec/tasks")
async def api_exec_tasks(session_id: Optional[str] = None):
    return _ok(execution.list_tasks(session_id=session_id) if execution else None, [])


@router.get("/api/sandbox/capabilities")
async def api_sandbox_capabilities():
    return {"python": True, "shell": True, "network": False}


# --- voice / misc -------------------------------------------------------
@router.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    if not voice:
        raise HTTPException(503, "voice unavailable")
    data = await file.read()
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    text = await voice.transcribe(data, suffix=suffix)
    return {"text": text}


@router.get("/api/tts")
async def api_tts(text: str = ""):
    if not voice:
        raise HTTPException(503, "voice unavailable")
    path = await voice.synthesize(text)
    if path is None or not Path(path).is_file():
        raise HTTPException(503, "synthesis failed")
    return FileResponse(path, media_type="audio/mpeg")


@router.post("/api/prompt/enhance")
async def api_prompt_enhance(payload: dict = Body(...)):
    return {"enhanced": str(payload.get("prompt", ""))}


@router.get("/api/consensus")
async def api_consensus():
    return {"status": "unavailable", "models": []}


# --- manifest signing ---------------------------------------------------
@router.post("/api/plugins/sign")
async def api_sign_payload(payload: dict = Body(...)):
    import plugin_signing

    content = str(payload.get("content") or "")
    return {"signature": plugin_signing.sign(content)}


@router.post("/api/plugins/verify")
async def api_verify_payload(payload: dict = Body(...)):
    import plugin_signing

    content = str(payload.get("content") or "")
    return {"valid": plugin_signing.verify(content, str(payload.get("signature") or ""))}


# --- update + crash reporting ------------------------------------------
@router.get("/api/updates/check")
async def api_update_check(current: str = ""):
    path = _BACKEND_DIR / "version.json"
    info = {"version": "6.1.0", "channel": "local", "update_available": False}
    if path.is_file():
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    info["update_available"] = bool(current) and str(info.get("version", "")) != str(current)
    return info


@router.post("/api/telemetry/crash")
async def api_crash_report(payload: dict = Body(...)):
    folder = _BACKEND_DIR / "data" / "crashes"
    folder.mkdir(parents=True, exist_ok=True)
    import time

    path = folder / f"crash-{int(time.time() * 1000)}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"ok": True, "path": str(path)}


# --- one-time OAuth client setup ---------------------------------------
@router.get("/api/integrations/oauth-config/{plugin_id}")
async def oauth_config_get(plugin_id: str):
    try:
        from integrations.providers import get_provider
    except Exception as exc:
        raise HTTPException(503, f"providers unavailable: {exc}") from exc
    spec = get_provider(plugin_id)
    if spec is None:
        raise HTTPException(404, f"no OAuth provider for {plugin_id}")
    return {
        "plugin_id": plugin_id,
        "name": spec.name,
        "client_id_env": spec.client_id_env,
        "client_secret_env": spec.client_secret_env,
        "client_id_set": bool(spec.client_id()),
        "client_secret_set": bool(spec.client_secret()),
        "configured": not bool(spec.missing_config()),
        "docs_url": spec.docs_url,
        "redirect_uri": os.getenv("OAUTH_REDIRECT_URI")
        or "http://127.0.0.1:7777/api/integrations/callback",
        "missing_config": spec.missing_config(),
    }


@router.post("/api/integrations/oauth-config/{plugin_id}")
async def oauth_config_set(plugin_id: str, payload: dict = Body(...)):
    try:
        from integrations.providers import get_provider
    except Exception as exc:
        raise HTTPException(503, f"providers unavailable: {exc}") from exc
    spec = get_provider(plugin_id)
    if spec is None:
        raise HTTPException(404, f"no OAuth provider for {plugin_id}")

    updates: Dict[str, str] = {}
    client_id = str(payload.get("client_id") or "").strip()
    client_secret = str(payload.get("client_secret") or "").strip()
    if client_id:
        updates[spec.client_id_env] = client_id
    if client_secret:
        updates[spec.client_secret_env] = client_secret
    if not updates:
        raise HTTPException(400, "client_id or client_secret is required")

    env_path = _BACKEND_DIR / ".env"
    text = env_path.read_text(encoding="utf-8-sig") if env_path.exists() else ""
    lines = text.splitlines()
    seen = set()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            lines[i] = f"{key}={updates[key]}"
            seen.add(key)
    for key, value in updates.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for key, value in updates.items():
        os.environ[key] = value
    try:
        import platform_secrets

        platform_secrets.set_many(updates)
    except Exception:
        pass

    return await oauth_config_get(plugin_id)


@router.post("/api/login")
async def api_login(payload: dict = Body(...)):
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not password:
        return {"ok": True, "token": "", "auth_required": False}
    if str(payload.get("password", "")) != password:
        raise HTTPException(401, "invalid credentials")
    import hashlib

    return {"ok": True, "token": hashlib.sha256(password.encode()).hexdigest(), "auth_required": True}
