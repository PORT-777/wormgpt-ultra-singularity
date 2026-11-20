# backend/tools/__init__.py
# 🔥😈 PORT 777 EVIL ☠️🔥👹 - Singularity Edition — Tool registry.
# Auto-discovers Tool subclasses and provides execute_tool/tool_schemas.

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Any, Dict, List

from .base import Tool, checkpoint_context

log = logging.getLogger("tools")

TOOL_REGISTRY: Dict[str, type[Tool]] = {}

_MUTATING_FILE_ACTIONS = {
    "write", "append", "copy", "move", "delete", "download", "extract",
    "patch", "save", "edit", "aob_patch",
}


def _discover() -> None:
    package = __name__
    for m in pkgutil.iter_modules(__path__):  # type: ignore[attr-defined]
        if m.name == "__init__":
            continue
        mod = importlib.import_module(f"{package}.{m.name}")
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, Tool) and obj is not Tool:
                name = getattr(obj, "name", obj.__name__)
                TOOL_REGISTRY[name] = obj


_discover()


def _candidate_paths(name: str, args: Dict[str, Any]) -> List[str]:
    if not isinstance(args, dict):
        return []
    action = str(args.get("action", "")).lower().strip()
    # Shell/Python/MCP are arbitrary; don't guess. Snapshot explicit file paths for file tools.
    if name in {"ShellCommander", "SystemCommander", "PythonInterpreter", "McpTool"}:
        return []
    if name not in {"UniversalFileManager", "FileSystemMaster", "FileMaster", "file_manager", "file_master"} and action not in _MUTATING_FILE_ACTIONS:
        return []
    out: List[str] = []
    for k in ("path", "dest", "target", "file", "filename", "output", "save_path"):
        v = args.get(k)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    seen = set()
    dedup = []
    for p in out:
        k = p.lower()
        if k not in seen:
            seen.add(k)
            dedup.append(p)
    return dedup


def _maybe_snapshot_before_edit(name: str, args: Dict[str, Any]) -> None:
    ctx = checkpoint_context()
    if not ctx or ctx.get("done"):
        return
    paths = _candidate_paths(name, args)
    if not paths:
        return
    files = ctx.get("files")
    if not isinstance(files, set):
        files = set()
        ctx["files"] = files
    for p in paths:
        files.add(p)
    # Create checkpoint once per run, before first mutating edit executes.
    if ctx.get("created"):
        return
    try:
        import checkpoint as ckpt
        sid = str(ctx.get("session_id") or "default")
        mid = str(ctx.get("message_id") or "")
        man = ckpt.create_checkpoint(sid, mid, sorted(files), kind="pre-edit")
        ctx["created"] = man.get("id")
        ctx["manifest"] = {"id": man.get("id"), "files": len(man.get("files") or []), "ts": man.get("ts")}
    except Exception as e:
        log.debug("checkpoint snapshot failed: %s", e)


async def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Execute a tool by name and return text output."""
    cls = TOOL_REGISTRY.get(name)
    if cls is None:
        return f"ERROR: unknown tool '{name}'. Available: {sorted(TOOL_REGISTRY)}"
    tool = cls()
    try:
        _maybe_snapshot_before_edit(name, args or {})
    except Exception:
        pass
    try:
        return await tool.run(**args)
    except TypeError as exc:
        return f"ERROR: bad args for {name}: {exc}"
    except Exception as exc:
        return f"ERROR: {name} raised {type(exc).__name__}: {exc}"


def tool_schemas() -> str:
    """Render tool specs for the system prompt."""
    lines = []
    for name in sorted(TOOL_REGISTRY):
        cls = TOOL_REGISTRY[name]
        lines.append(f"- {getattr(cls, 'name', name)}: {getattr(cls, 'description', '')}")
        ex = getattr(cls, "example", {})
        if ex:
            lines.append(f"  Input JSON example: {ex}")
    return "\n".join(lines)


__all__ = ["TOOL_REGISTRY", "execute_tool", "tool_schemas", "Tool"]
