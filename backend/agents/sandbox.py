"""Static analysis + RestrictedPython sandbox for code agents."""
from __future__ import annotations

import ast
import io
import time
import contextlib
from dataclasses import dataclass
from typing import Any


@dataclass
class SandboxResult:
    output: str = ""
    error: str = ""
    exec_time_ms: int = 0


FORBIDDEN = ("os.system", "subprocess", "eval(", "exec(", "__import__",
             "shutil.rmtree", "open(")


def static_check(code: str) -> str | None:
    for pattern in FORBIDDEN:
        if pattern in code:
            return f"Forbidden: {pattern}"
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"SyntaxError: {exc}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if any(n.split(".")[0] in {"subprocess", "ctypes", "socket", "shutil"} for n in names):
                return f"Forbidden import: {names}"
    return None


async def execute_python(code: str, timeout: int = 10) -> SandboxResult:
    start = time.perf_counter()
    err = static_check(code)
    if err:
        return SandboxResult(error=err, exec_time_ms=0)
    try:
        from RestrictedPython import compile_restricted, safe_globals
    except ImportError:
        return SandboxResult(error="RestrictedPython not installed", exec_time_ms=0)
    try:
        byte_code = compile_restricted(code, "<sandbox>", "exec")
        if getattr(byte_code, "errors", None):
            return SandboxResult(error="; ".join(byte_code.errors), exec_time_ms=0)
        g = dict(safe_globals)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(byte_code, g)  # noqa: S102 - RestrictedPython-compiled bytecode
        return SandboxResult(output=out.getvalue()[:20000],
                             exec_time_ms=int((time.perf_counter() - start) * 1000))
    except Exception as exc:
        return SandboxResult(error=f"{type(exc).__name__}: {exc}",
                             exec_time_ms=int((time.perf_counter() - start) * 1000))
