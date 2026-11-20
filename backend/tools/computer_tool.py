"""Agent-facing tools for the real AI Computer subsystem."""
from __future__ import annotations

import json
import shlex
from typing import Any

from .base import Tool


def _manager():
    from computer.manager import get_manager

    return get_manager()


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)[:40000]


class ComputerTool(Tool):
    name = "ComputerTool"
    description = (
        "Manage real isolated Linux computers. Actions: create, start, stop, restart, delete, "
        "status, list, resources, providers. Modes: temporary or persistent."
    )
    example = {"action": "create", "mode": "temporary", "user_id": "default_user"}

    async def run(self, action: str = "", computer_id: str = "", user_id: str = "default_user",
                  mode: str = "temporary", name: str = "", resources: dict | None = None,
                  provider: str = "", **_: Any) -> str:
        try:
            m = _manager()
            if action == "create":
                return _dump(m.create(user_id=user_id, mode=mode, name=name,
                                      resources=resources, provider=provider or None))
            if action == "start":
                return _dump(m.start(computer_id, user_id))
            if action == "stop":
                return _dump(m.stop(computer_id, user_id))
            if action == "restart":
                return _dump(m.restart(computer_id, user_id))
            if action == "delete":
                return _dump({"deleted": m.delete(computer_id, user_id)})
            if action == "status":
                return _dump(m.get(computer_id, user_id))
            if action == "list":
                return _dump(m.list(user_id))
            if action == "resources":
                return _dump(m.resources(computer_id, user_id))
            if action == "providers":
                from computer.manager import provider_status

                return _dump(provider_status())
            return "ERROR: ComputerTool action must be create|start|stop|restart|delete|status|list|resources|providers"
        except Exception as exc:
            return f"ERROR: ComputerTool {action} failed: {type(exc).__name__}: {exc}"


class TerminalTool(Tool):
    name = "TerminalTool"
    description = (
        "Execute real shell commands inside a Linux computer. Actions: execute, session, history. "
        "Returns actual stdout, stderr and exit code."
    )
    example = {"action": "execute", "computer_id": "cmp-...", "command": "uname -a"}

    async def run(self, action: str = "execute", computer_id: str = "", user_id: str = "default_user",
                  command: str = "", cwd: str = "", timeout: int = 60,
                  session_id: str = "", env: dict | None = None, **_: Any) -> str:
        try:
            m = _manager()
            job_id = m.create_job(computer_id, user_id)
            if action in ("execute", "session"):
                return _dump(m.execute(computer_id, user_id, command, cwd=cwd, timeout=timeout,
                                       env=env, session_id=session_id, job_id=job_id))
            if action == "history":
                from computer import store

                return _dump(store.logs(job_id))
            return "ERROR: TerminalTool action must be execute|session|history"
        except Exception as exc:
            return f"ERROR: TerminalTool failed: {type(exc).__name__}: {exc}"


class FilesystemTool(Tool):
    name = "FilesystemTool"
    description = (
        "Real filesystem operations inside a Linux computer: list, read, write, delete, mkdir, "
        "search, archive, extract."
    )
    example = {"action": "list", "computer_id": "cmp-...", "path": "/workspace"}

    async def run(self, action: str = "", computer_id: str = "", user_id: str = "default_user",
                  path: str = "/workspace", content: str = "", query: str = "",
                  destination: str = "", **_: Any) -> str:
        try:
            m = _manager()
            if action == "list":
                return _dump(m.list_files(computer_id, user_id, path))
            if action == "read":
                return m.read_file(computer_id, user_id, path)[:40000]
            if action == "write":
                return _dump({"written": m.write_file(computer_id, user_id, path, content)})
            if action == "delete":
                return _dump({"deleted": m.delete_file(computer_id, user_id, path)})
            if action == "mkdir":
                return _dump(m.execute(computer_id, user_id, f"mkdir -p {shlex.quote(path)}"))
            if action == "search":
                return _dump(m.execute(computer_id, user_id,
                                       f"grep -RIn --exclude-dir=.git {shlex.quote(query)} {shlex.quote(path)} | head -200"))
            if action == "archive":
                return _dump(m.execute(computer_id, user_id,
                                       f"tar -czf {shlex.quote(destination or path + '.tar.gz')} -C {shlex.quote(path)} ."))
            if action == "extract":
                return _dump(m.execute(computer_id, user_id,
                                       f"mkdir -p {shlex.quote(destination)} && tar -xzf {shlex.quote(path)} -C {shlex.quote(destination)}"))
            return "ERROR: FilesystemTool action must be list|read|write|delete|mkdir|search|archive|extract"
        except Exception as exc:
            return f"ERROR: FilesystemTool failed: {type(exc).__name__}: {exc}"


class BrowserTool(Tool):
    name = "BrowserTool"
    description = (
        "Real Playwright browser automation inside a Linux computer. Actions: open, navigate, "
        "content, click, fill, type, select, scroll, screenshot, elements, tabs, takeover."
    )
    example = {"action": "open", "computer_id": "cmp-...", "url": "https://example.com"}

    async def run(self, action: str = "", computer_id: str = "", user_id: str = "default_user",
                  url: str = "", selector: str = "", text: str = "", value: str = "",
                  session_id: str = "default", **_: Any) -> str:
        try:
            if action == "takeover":
                return _dump({"status": "paused", "message": "Automation paused. User completes the step manually; call resume to continue."})
            payload = {"op": action, "session_id": session_id, "url": url, "selector": selector,
                       "text": text, "value": value}
            return _dump(_manager().browser(computer_id, user_id, payload))
        except Exception as exc:
            return f"ERROR: BrowserTool failed: {type(exc).__name__}: {exc}"


class ProcessTool(Tool):
    name = "ProcessTool"
    description = "List, stop and inspect real processes in a Linux computer."
    example = {"action": "list", "computer_id": "cmp-..."}

    async def run(self, action: str = "list", computer_id: str = "", user_id: str = "default_user",
                  pid: str = "", **_: Any) -> str:
        try:
            m = _manager()
            if action == "list":
                return _dump(m.processes(computer_id, user_id))
            if action == "stop":
                return _dump({"stopped": m.stop_process(computer_id, user_id, pid)})
            return "ERROR: ProcessTool action must be list|stop"
        except Exception as exc:
            return f"ERROR: ProcessTool failed: {type(exc).__name__}: {exc}"


class DevelopmentTool(Tool):
    name = "DevelopmentTool"
    description = (
        "Build and verify projects inside a Linux computer: install_dependencies, run_project, "
        "build, test, preview, get_errors."
    )
    example = {"action": "install_dependencies", "computer_id": "cmp-...", "command": "pip install requests"}

    async def run(self, action: str = "", computer_id: str = "", user_id: str = "default_user",
                  command: str = "", cwd: str = "/workspace", port: int = 0, **_: Any) -> str:
        try:
            m = _manager()
            mapping = {
                "install_dependencies": command,
                "run_project": command or "python3 -m http.server 8000",
                "build": command or "npm run build",
                "test": command or "python3 -m pytest -q",
                "get_errors": "find . -type f \\( -name '*.log' -o -name '*.err' \\) -print | head -50",
            }
            if action == "preview":
                return _dump({"preview": f"http://127.0.0.1:{port or 8000}",
                              "note": "Use the computer's port forwarding UI to expose this port."})
            cmd = mapping.get(action)
            if not cmd:
                return "ERROR: DevelopmentTool action must be install_dependencies|run_project|build|test|preview|get_errors"
            return _dump(m.execute(computer_id, user_id, cmd, cwd=cwd, timeout=600))
        except Exception as exc:
            return f"ERROR: DevelopmentTool failed: {type(exc).__name__}: {exc}"
