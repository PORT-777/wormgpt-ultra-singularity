"""OpenHands-inspired isolated code execution environment."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import os


@dataclass
class CommandResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1


class CodeEnvironment:
    SAFE_COMMANDS = {"python", "python3", "ls", "pwd", "cat", "echo", "wc", "head", "tail"}

    def __init__(self, base: str | None = None, session_id: str | None = None):
        base = base or os.getenv("CODE_WORKSPACE_BASE", "workspace/code_env")
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.workspace_path = Path(base) / self.session_id
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        target = (self.workspace_path / path.lstrip("/\\")).resolve()
        if self.workspace_path.resolve() not in target.parents and target != self.workspace_path.resolve():
            raise ValueError("path escapes code workspace")
        return target

    async def write_file(self, path: str, content: str) -> str:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return str(p)

    async def read_file(self, path: str) -> str:
        return self._resolve(path).read_text(encoding="utf-8", errors="replace")

    async def run_command(self, cmd: str, timeout: int = 30) -> CommandResult:
        parts = str(cmd).strip().split()
        if not parts or parts[0] not in self.SAFE_COMMANDS:
            return CommandResult(stderr=f"command not allowed: {parts[0] if parts else ''}")
        proc = await asyncio.create_subprocess_exec(
            *parts, cwd=str(self.workspace_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return CommandResult(out.decode("utf-8", "replace")[:20000],
                                 err.decode("utf-8", "replace")[:20000],
                                 proc.returncode or 0)
        except asyncio.TimeoutError:
            proc.kill()
            return CommandResult(stderr="timeout", exit_code=-1)

    async def run_python(self, code: str) -> dict[str, Any]:
        from agents.sandbox import execute_python
        r = await execute_python(code, timeout=10)
        return {"output": r.output, "error": r.error, "exec_time_ms": r.exec_time_ms}

    async def list_files(self) -> list[str]:
        return [str(p.relative_to(self.workspace_path))
                for p in self.workspace_path.rglob("*") if p.is_file()]

    async def reset(self) -> None:
        import shutil
        shutil.rmtree(self.workspace_path, ignore_errors=True)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
