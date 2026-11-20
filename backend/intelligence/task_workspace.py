"""Per-task isolated workspaces with original-artifact preservation."""
from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND_DIR / "workspace" / "intelligence_tasks"
_ROOT.mkdir(parents=True, exist_ok=True)


def _task_dir(task_id: str) -> Path:
    base = (_ROOT / task_id).resolve()
    if _ROOT.resolve() not in base.parents and base != _ROOT.resolve():
        raise ValueError("invalid task id")
    return base


def create_task(name: str = "analysis", source: str | None = None) -> Dict[str, Any]:
    tid = f"{int(time.time())}-{secrets.token_hex(4)}"
    base = _task_dir(tid)
    for sub in ("input", "project", "analysis", "extracted", "reports", "output"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    meta: Dict[str, Any] = {
        "id": tid,
        "name": name,
        "created": time.time(),
        "source": source or "",
        "original_hash": "",
        "paths": {k: str(base / k) for k in ("input", "project", "analysis", "extracted", "reports", "output")},
    }
    if source:
        src = Path(source).expanduser().resolve()
        if src.is_file():
            dest = base / "input" / src.name
            shutil.copy2(src, dest)
            meta["original_hash"] = hashlib.sha256(dest.read_bytes()).hexdigest()
            meta["original_name"] = src.name
        elif src.is_dir():
            dest = base / "project"
            for item in src.iterdir():
                target = dest / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "node_modules"))
                else:
                    shutil.copy2(item, target)
            meta["source_type"] = "directory"
    (base / "task.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def get_task(task_id: str) -> Dict[str, Any]:
    path = _task_dir(task_id) / "task.json"
    if not path.is_file():
        raise ValueError(f"unknown task: {task_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_report(task_id: str, name: str, payload: Dict[str, Any]) -> str:
    base = _task_dir(task_id)
    path = base / "reports" / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return str(path)


def export_task(task_id: str) -> str:
    base = _task_dir(task_id)
    out = base / "output" / f"{task_id}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in base.rglob("*"):
            if not item.is_file() or item == out:
                continue
            zf.write(item, item.relative_to(base))
    return str(out)


def list_tasks(limit: int = 50) -> list:
    out = []
    for item in sorted(_ROOT.iterdir(), reverse=True)[:limit]:
        meta = item / "task.json"
        if meta.is_file():
            out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out
