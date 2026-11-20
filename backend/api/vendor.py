"""Vendored reference repositories exposed to the UI.

The four upstream projects live under <project>/vendor. This module reports
what is checked out so the Workspace panel can link them without pulling the
whole tree into the conversation.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/vendor", tags=["vendor"])

_PROJECT_DIR = Path(__file__).resolve().parents[2]
_VENDOR_DIR = _PROJECT_DIR / "vendor"

REPOS = [
    {
        "id": "autogpt",
        "name": "AutoGPT",
        "url": "https://github.com/significant-gravitas/autogpt",
        "role": "autonomous agent platform / prompt and tool architecture",
    },
    {
        "id": "claude-skills",
        "name": "Claude Skills",
        "url": "https://github.com/alirezarezvani/claude-skills",
        "role": "reusable skill packs and prompt playbooks",
    },
    {
        "id": "openhands",
        "name": "OpenHands",
        "url": "https://github.com/OpenHands/openhands",
        "role": "agent runtime, tool execution and workspace patterns",
    },
    {
        "id": "ECC",
        "name": "ECC",
        "url": "https://github.com/affaan-m/ECC",
        "role": "extended capability catalog / engineering references",
    },
    {
        "id": "hermes-agent",
        "name": "Hermes Agent",
        "url": "https://github.com/nousresearch/hermes-agent",
        "role": "NousResearch autonomous agent patterns and tool-use research",
    },
    {
        "id": "lunar-source",
        "name": "Lunar Source (selected files)",
        "url": "",
        "role": "real local reference files: URL policy, secret store, tool pattern, defaults",
    },
]


def _commit(path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=8,
        )
        return (out.stdout or "").strip() or "unknown"
    except Exception:
        return "unknown"


_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}


def _file_count(path: Path) -> int:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "ls-files"],
            capture_output=True, text=True, timeout=20,
        )
        count = sum(1 for line in (out.stdout or "").splitlines() if line.strip())
        if count:
            return count
    except Exception:
        pass
    try:
        return sum(1 for item in path.rglob("*") if item.is_file())
    except Exception:
        return 0


def _summary(path: Path) -> str:
    for name in ("README.md", "readme.md", "README.rst"):
        candidate = path / name
        if candidate.is_file():
            try:
                lines = [line.strip() for line in candidate.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
                return " ".join(lines[:3])[:280]
            except Exception:
                return ""
    return ""


@router.get("/repos")
async def list_repos() -> Dict[str, Any]:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < 120:
        return _CACHE["data"]
    items: List[Dict[str, Any]] = []
    for meta in REPOS:
        path = _VENDOR_DIR / meta["id"]
        exists = path.is_dir()
        files = _file_count(path) if exists else 0
        items.append({
            **meta,
            "path": str(path),
            "present": exists,
            "commit": _commit(path) if exists else "",
            "file_count": files,
            "summary": _summary(path) if exists else "",
        })
    result = {"vendor_dir": str(_VENDOR_DIR), "repos": items}
    _CACHE["ts"] = now
    _CACHE["data"] = result
    return result


@router.get("/repos/{repo_id}")
async def repo_detail(repo_id: str) -> Dict[str, Any]:
    data = await list_repos()
    for item in data["repos"]:
        if item["id"] == repo_id:
            return item
    raise HTTPException(404, f"unknown vendored repo: {repo_id}")
