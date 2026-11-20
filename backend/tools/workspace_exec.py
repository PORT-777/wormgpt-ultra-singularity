"""
Agent tools bound to the active Universal Execution task.

These tools operate *only* inside the current task workspace
(``<workspace>/data/exec/tasks/<id>/workspace``).  They are real: shell
commands spawn processes, Python runs a subprocess, files touch the disk.
"""
from __future__ import annotations

import json
from typing import Any

import execution
import runtime_env
from .base import Tool


def _fmt_run(res: dict) -> str:
    if res.get("requires_approval"):
        return ("ERROR: approval required before running this command "
                f"(risk={res.get('risk')}): {res.get('reason')} — ask the user to approve it.")
    if res.get("background"):
        return f"Started in background: {res.get('command')}"
    out = [f"[exit code {res.get('exit_code')}]"]
    if res.get("timeout"):
        out.append(f"[timeout after {res.get('duration_ms', 0) / 1000:.1f}s]")
    if res.get("stdout"):
        out.append("--- stdout ---\n" + str(res["stdout"]))
    if res.get("stderr"):
        out.append("--- stderr ---\n" + str(res["stderr"]))
    if res.get("error"):
        out.append("--- error ---\n" + str(res["error"]))
    return "\n".join(out) if len(out) > 1 else "[no output, exit code 0]"


class WorkspaceExec(Tool):
    name = "WorkspaceExec"
    description = (
        "Execute a REAL shell command inside the current execution task workspace "
        "and return its actual stdout/stderr/exit code. Use this to build, test, "
        "inspect and modify the project instead of printing code. "
        "Args: {'command': 'python --version', 'timeout': 60, 'shell': 'powershell'|'cmd'|'bash'}."
    )
    example = {"command": "Get-ChildItem -Force | Select-Object Name,Length"}

    async def run(self, command: str = "", timeout: int = 120, shell: str = "auto", **_: Any) -> str:
        command = str(command or "").strip()
        if not command:
            return "ERROR: empty command"
        tid = execution.get_active_task()
        if not tid:
            return ("ERROR: no active execution task. The user must start an execution "
                    "environment (or attach a project) before shell execution.")
        try:
            res = await execution.run_command(tid, command, shell=shell, timeout=int(timeout or 120))
        except Exception as exc:
            return f"ERROR: {type(exc).__name__}: {exc}"
        return _fmt_run(res)


class WorkspacePython(Tool):
    name = "WorkspacePython"
    description = (
        "Run a real Python snippet inside the current execution task workspace. "
        "stdout/stderr are returned to you. Args: {'code': 'print(2+2)', 'timeout': 60}."
    )
    example = {"code": "import os; print(os.getcwd())"}

    async def run(self, code: str = "", timeout: int = 60, **_: Any) -> str:
        code = str(code or "")
        if not code.strip():
            return "ERROR: empty code"
        tid = execution.get_active_task()
        if not tid:
            return "ERROR: no active execution task."
        try:
            res = await execution.run_python(tid, code, timeout=int(timeout or 60))
        except Exception as exc:
            return f"ERROR: {type(exc).__name__}: {exc}"
        return _fmt_run(res)


class WorkspaceFiles(Tool):
    name = "WorkspaceFiles"
    description = (
        "Read/write/list files inside the current execution task workspace. "
        "Args: {'action': 'list'|'read'|'write'|'delete', 'path': 'src/main.py', "
        "'content': '...'}. Paths may not escape the task workspace."
    )
    example = {"action": "list", "path": "."}

    async def run(self, action: str = "list", path: str = ".", content: str = "", **_: Any) -> str:
        tid = execution.get_active_task()
        if not tid:
            return "ERROR: no active execution task."
        action = str(action or "list").lower()
        try:
            if action == "list":
                data = execution.list_files(tid)
                rows = data.get("files", [])[:300]
                lines = [f"{'DIR ' if f['is_dir'] else 'FILE'} {f['path']}" for f in rows]
                return (f"{data.get('count', 0)} entries. project={json.dumps(data.get('project', {}), ensure_ascii=False)}\n"
                        + "\n".join(lines))
            if action == "read":
                data = execution.read_file(tid, path)
                if data.get("binary"):
                    return f"{path}: binary file ({data.get('size')} bytes)"
                return f"{path} ({data.get('size')} bytes):\n" + str(data.get("content", ""))
            if action == "write":
                res = execution.write_file(tid, path, content)
                return f"wrote {res['path']} ({res['written']} chars)"
            if action == "delete":
                res = execution.delete_path(tid, path)
                return f"deleted {res['deleted']}"
            return f"ERROR: unknown action {action!r}"
        except Exception as exc:
            return f"ERROR: {type(exc).__name__}: {exc}"


class EnvironmentInfo(Tool):
    name = "EnvironmentInfo"
    description = (
        "Return the VERIFIED execution environment fingerprint: OS, distribution, "
        "kernel, architecture, runtime type, workspace, capabilities and installed "
        "tools. Use before choosing OS-specific commands."
    )
    example = {}

    async def run(self, **_: Any) -> str:
        s = runtime_env.summary()
        caps = s.get("capabilities") or {}
        tools = runtime_env.tool_catalog()
        return json.dumps({
            "os": s.get("name"), "version": s.get("version"),
            "distro": s.get("distro_name") or s.get("distro_id"),
            "arch": s.get("arch"), "kernel": s.get("kernel"),
            "runtime_type": s.get("runtime_type"),
            "workspace": s.get("workspace"),
            "capabilities": caps,
            "installed_tools": tools.get("installed", []),
        }, ensure_ascii=False, indent=1)