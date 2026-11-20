"""HTTP surface for the Code & Binary Intelligence Engine."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from intelligence import binary_intel, project_intel, task_workspace, toolchain

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/toolchain")
async def api_toolchain():
    return toolchain.discover()


@router.post("/agents/plan")
async def api_agents_plan(payload: dict = Body(...)):
    from intelligence import agents

    return {
        "plan": agents.plan(
            str(payload.get("task") or "analyze"),
            str(payload.get("artifact_type") or "project"),
        )
    }


@router.get("/tasks")
async def api_tasks():
    return {"tasks": task_workspace.list_tasks()}


@router.post("/tasks")
async def api_create_task(payload: dict = Body(...)):
    return task_workspace.create_task(str(payload.get("name") or "analysis"), str(payload.get("source") or ""))


@router.post("/project/scan")
async def api_scan(payload: dict = Body(...)):
    path = str(payload.get("path") or "")
    if not path:
        raise HTTPException(400, "path is required")
    return project_intel.scan_project(path, limit=int(payload.get("limit") or 4000))


@router.post("/project/symbol")
async def api_symbol(payload: dict = Body(...)):
    return {
        "matches": project_intel.find_symbol(str(payload.get("path") or ""), str(payload.get("query") or "")),
        "callers": project_intel.call_hierarchy(str(payload.get("path") or ""), str(payload.get("query") or "")),
    }


@router.post("/project/quality")
async def api_quality(payload: dict = Body(...)):
    return project_intel.code_quality(str(payload.get("path") or ""))


@router.post("/binary/analyze")
async def api_analyze(payload: dict = Body(...)):
    path = str(payload.get("path") or "")
    if not path:
        raise HTTPException(400, "path is required")
    return binary_intel.analyze(path, include_disasm=bool(payload.get("include_disasm")))


@router.post("/binary/identify")
async def api_identify(payload: dict = Body(...)):
    return binary_intel.identify(str(payload.get("path") or ""))


@router.post("/tasks/{task_id}/report")
async def api_report(task_id: str, payload: dict = Body(...)):
    try:
        return {"path": task_workspace.save_report(task_id, str(payload.get("name") or "report"), payload.get("report") or {})}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/tasks/{task_id}/export")
async def api_export(task_id: str):
    try:
        return {"path": task_workspace.export_task(task_id)}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
