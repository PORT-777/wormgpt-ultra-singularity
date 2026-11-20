"""
Tool :: SystemCommander (Full Access Mode only)

Executes terminal commands on the host machine and returns stdout,
stderr plus exit code — for installs, builds, git, process control,
system status monitoring, etc.

Zero refusal: every command the operator asks for is executed. No
denylist, no "destructive" blocks, no refusals — the operator owns
the machine and decides what runs.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Any

import configs as config
from .base import Tool, full_access, _active_workspace


class SystemCommander(Tool):
    name = "SystemCommander"
    description = (
        "Execute a shell command on the host and monitor its output/status: "
        "{'command': 'python -m pip list'} — Full Access Mode required. "
        "No denylist, no refusals — every command is executed as requested."
    )
    example = {"command": "python --version"}

    async def run(self, command: str = "", **_: Any) -> str:
        if not full_access():
            return ("ERROR: SystemCommander requires FULL ACCESS mode — "
                    "toggle it in the UI for this request.")
        command = (command or "").strip()
        if not command:
            return "ERROR: empty command"
        if sys.platform == "win32" and not _looks_like_powershell(command):
            command = command  # cmd.exe-friendly anyway

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(_active_workspace() or config.WORKSPACE_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            return f"ERROR: shell not found: {exc}"

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=config.SHELL_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            return (f"ERROR: command exceeded {config.SHELL_TIMEOUT}s "
                    f"(likely waiting for interactive input) and was killed")

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        report = f"[exit code {proc.returncode}]"
        if out:
            report += "\n--- stdout ---\n" + out[: config.SHELL_MAX_OUTPUT]
        if err:
            report += "\n--- stderr ---\n" + err[: config.SHELL_MAX_OUTPUT // 2]
        return report or "[no output, exit code 0]"


def _looks_like_powershell(cmd: str) -> bool:
    # shell=True on Windows uses cmd.exe; that's fine for the overlap case
    return False
