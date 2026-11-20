"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Workspace API
FastAPI endpoints for workspace attachment and manipulation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

import sys
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workspace_manager import workspace_manager

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


# --------------------------------------------------------------------------- #
#  Request/Response Models
# --------------------------------------------------------------------------- #

class AttachRequest(BaseModel):
    workspace_id: str
    path: str


class DetachRequest(BaseModel):
    workspace_id: str


class ListFilesRequest(BaseModel):
    workspace_id: str
    directory: str = "."


class ReadFileRequest(BaseModel):
    workspace_id: str
    file_path: str


class WriteFileRequest(BaseModel):
    workspace_id: str
    file_path: str
    content: str


class EditFileRequest(BaseModel):
    workspace_id: str
    file_path: str
    old_string: str
    new_string: str
    replace_all: bool = False


class ExecuteCommandRequest(BaseModel):
    workspace_id: str
    command: str
    cwd: str = "."


class GetTreeRequest(BaseModel):
    workspace_id: str
    directory: str = "."
    max_depth: int = 3


# --------------------------------------------------------------------------- #
#  Endpoints
# --------------------------------------------------------------------------- #

@router.post("/attach")
async def attach_workspace(req: AttachRequest):
    """Attach a local directory as a workspace."""
    result = workspace_manager.attach_workspace(req.workspace_id, req.path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/list")
async def list_workspaces():
    """List all attached workspaces."""
    return {"workspaces": workspace_manager.list_workspaces()}


@router.post("/detach")
async def detach_workspace(req: DetachRequest):
    """Detach a workspace."""
    result = workspace_manager.detach_workspace(req.workspace_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/files/list")
async def list_files(req: ListFilesRequest):
    """List files and directories within a workspace."""
    result = workspace_manager.list_files(req.workspace_id, req.directory)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/files/read")
async def read_file(req: ReadFileRequest):
    """Read a file from within a workspace."""
    result = workspace_manager.read_file(req.workspace_id, req.file_path)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/files/write")
async def write_file(req: WriteFileRequest):
    """Write content to a file within a workspace."""
    result = workspace_manager.write_file(req.workspace_id, req.file_path, req.content)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/files/edit")
async def edit_file(req: EditFileRequest):
    """Perform targeted text replacement within a file."""
    result = workspace_manager.edit_file(
        req.workspace_id, req.file_path, req.old_string, req.new_string, req.replace_all
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/command/execute")
async def execute_command(req: ExecuteCommandRequest):
    """Execute a shell command within a workspace directory."""
    result = workspace_manager.execute_command(req.workspace_id, req.command, req.cwd)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/tree")
async def get_tree(req: GetTreeRequest):
    """Generate a tree-like structure of the workspace directory."""
    result = workspace_manager.get_tree(req.workspace_id, req.directory, req.max_depth)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result