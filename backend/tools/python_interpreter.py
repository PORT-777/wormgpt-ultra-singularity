"""
Tool :: PythonInterpreter

Executes Python snippets in an isolated subprocess under the workspace
directory, with a hard timeout and full stdout/stderr capture. Because
the cwd is the agent workspace, snippets can import files the agent
previously wrote via FileManager.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

import configs as config
from .base import Tool


class PythonInterpreter(Tool):
    name = "PythonInterpreter"
    description = (
        "Run a Python code snippet to compute, transform data, or test code. "
        "Print results to stdout; stdout is returned to you."
    )
    example = {"code": "print(sum(range(10)))"}

    async def run(self, code: str = "", **_: Any) -> str:
        if not code.strip():
            return "ERROR: empty code"

        # Materialise the snippet into a temp script (works cross-platform)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(code)
            script = fh.name

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script,
                cwd=str(_active_workspace() or config.WORKSPACE_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=config.TOOL_EXEC_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                return f"ERROR: execution exceeded {config.TOOL_EXEC_TIMEOUT}s timeout"

            out = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()
            result = f"[exit code {proc.returncode}]"
            if out:
                result += f"\n--- stdout ---\n{out}"
            if err:
                result += f"\n--- stderr ---\n{err}"
            return result or "[no output]"
        finally:
            Path(script).unlink(missing_ok=True)
