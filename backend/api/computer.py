"""HTTP API for the AI Computer subsystem."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException

from computer.manager import get_manager, provider_status

router = APIRouter(prefix="/api/computer", tags=["ai-computer"])


def _user(x_user_id: Optional[str]) -> str:
    return x_user_id or "default_user"


@router.get("/providers")
async def providers():
    return {"providers": provider_status()}


@router.get("/computers")
async def computers(x_user_id: Optional[str] = Header(None)):
    return {"computers": get_manager().list(_user(x_user_id))}


@router.post("/computers")
async def create_computer(payload: dict = Body(...), x_user_id: Optional[str] = Header(None)):
    try:
        return get_manager().create(
            user_id=_user(x_user_id), mode=str(payload.get("mode") or "temporary"),
            name=str(payload.get("name") or ""), resources=payload.get("resources"),
            provider=str(payload.get("provider") or "") or None,
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/computers/{computer_id}")
async def get_computer(computer_id: str, x_user_id: Optional[str] = Header(None)):
    try:
        return get_manager().get(computer_id, _user(x_user_id))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/computers/{computer_id}/start")
async def start_computer(computer_id: str, x_user_id: Optional[str] = Header(None)):
    return get_manager().start(computer_id, _user(x_user_id))


@router.post("/computers/{computer_id}/stop")
async def stop_computer(computer_id: str, x_user_id: Optional[str] = Header(None)):
    return get_manager().stop(computer_id, _user(x_user_id))


@router.post("/computers/{computer_id}/restart")
async def restart_computer(computer_id: str, x_user_id: Optional[str] = Header(None)):
    return get_manager().restart(computer_id, _user(x_user_id))


@router.delete("/computers/{computer_id}")
async def delete_computer(computer_id: str, x_user_id: Optional[str] = Header(None)):
    return {"deleted": get_manager().delete(computer_id, _user(x_user_id))}


@router.get("/computers/{computer_id}/resources")
async def resources(computer_id: str, x_user_id: Optional[str] = Header(None)):
    return get_manager().resources(computer_id, _user(x_user_id))


@router.post("/computers/{computer_id}/execute")
async def execute(computer_id: str, payload: dict = Body(...), x_user_id: Optional[str] = Header(None)):
    return get_manager().execute(
        computer_id, _user(x_user_id), str(payload.get("command") or ""),
        cwd=str(payload.get("cwd") or ""), timeout=int(payload.get("timeout") or 60),
        env=payload.get("env"), session_id=str(payload.get("session_id") or ""),
    )


@router.post("/computers/{computer_id}/files/list")
async def list_files(computer_id: str, payload: dict = Body(default={}), x_user_id: Optional[str] = Header(None)):
    return {"files": get_manager().list_files(computer_id, _user(x_user_id),
                                              str(payload.get("path") or "/workspace"))}


@router.post("/computers/{computer_id}/files/read")
async def read_file(computer_id: str, payload: dict = Body(...), x_user_id: Optional[str] = Header(None)):
    return {"content": get_manager().read_file(computer_id, _user(x_user_id), str(payload.get("path") or ""))[:40000]}


@router.post("/computers/{computer_id}/files/write")
async def write_file(computer_id: str, payload: dict = Body(...), x_user_id: Optional[str] = Header(None)):
    return {"written": get_manager().write_file(computer_id, _user(x_user_id),
                                                str(payload.get("path") or ""), str(payload.get("content") or ""))}


@router.post("/computers/{computer_id}/processes")
async def processes(computer_id: str, x_user_id: Optional[str] = Header(None)):
    return {"processes": get_manager().processes(computer_id, _user(x_user_id))}


@router.post("/computers/{computer_id}/browser")
async def browser(computer_id: str, payload: dict = Body(...), x_user_id: Optional[str] = Header(None)):
    return get_manager().browser(computer_id, _user(x_user_id), payload)


@router.get("/computers/{computer_id}/screenshot")
async def screenshot(computer_id: str, x_user_id: Optional[str] = Header(None)):
    path = get_manager().screenshot(computer_id, _user(x_user_id))
    return {"path": path}


@router.get("/jobs/{job_id}")
async def job(job_id: str, x_user_id: Optional[str] = Header(None)):
    from computer import store

    row = get_manager().job(job_id, _user(x_user_id))
    if not row:
        raise HTTPException(404, "job not found")
    row["logs"] = store.logs(job_id)
    return row
