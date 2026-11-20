"""Git operations inside an execution-task workspace.

Real `git` subprocess calls, capped output, short timeouts.  Never guesses
success: the return value always carries the exit code and raw output.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import execution

log = logging.getLogger("gitops")

MAX_OUTPUT = 20000
DEFAULT_TIMEOUT = 25


def _git(workdir: Path, args: List[str], timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    if not workdir or not Path(workdir).is_dir():
        return {"ok": False, "error": "task workspace not found", "code": -1,
                "output": ""}
    cmd = ["git", "-C", str(workdir), "--no-pager",
           "-c", "user.name=PORT777", "-c", "user.email=port777@local",
           *args]
    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    # Force this workdir to be its own repository: never walk up into a
    # parent repo (D:\xxxGPT is itself a git repo).
    env["GIT_DIR"] = str(Path(workdir) / ".git")
    env["GIT_WORK_TREE"] = str(workdir)
    env["GIT_CEILING_DIRECTORIES"] = str(Path(workdir).parent)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, env=env,
                              encoding="utf-8", errors="replace")
        out = ((proc.stdout or "") + (proc.stderr or ""))
        if len(out) > MAX_OUTPUT:
            out = out[:MAX_OUTPUT] + "\n...[truncated]"
        return {"ok": proc.returncode == 0, "code": proc.returncode,
                "cmd": " ".join(cmd[3:]), "output": out.strip()}
    except FileNotFoundError:
        return {"ok": False, "error": "git not installed", "code": -1,
                "output": ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"git timed out after {timeout}s",
                "code": -1, "output": ""}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "code": -1, "output": ""}


def _task_dir(task_id: str) -> Path:
    task = execution.load_task(str(task_id))
    if not task:
        raise execution.EnvironmentUnavailable(
            requested=str(task_id), reason=f"task {task_id} not found",
            available=[])
    return Path(task["workdir"]).resolve()


def init(task_id: str) -> Dict[str, Any]:
    return _git(_task_dir(task_id), ["init"])


def status(task_id: str) -> Dict[str, Any]:
    return _git(_task_dir(task_id), ["status", "--short", "--branch"])


def log(task_id: str, n: int = 20) -> Dict[str, Any]:
    return _git(_task_dir(task_id),
                ["log", f"-n{max(1, min(int(n or 20), 100))}",
                 "--oneline", "--decorate"])


def diff(task_id: str, target: str = "") -> Dict[str, Any]:
    args = ["diff"]
    if target:
        args.append(str(target))
    return _git(_task_dir(task_id), args)


def branches(task_id: str) -> Dict[str, Any]:
    return _git(_task_dir(task_id), ["branch", "-a"])


def add(task_id: str, paths: List[str] | None = None) -> Dict[str, Any]:
    targets = [str(p) for p in (paths or []) if str(p).strip()] or ["-A"]
    return _git(_task_dir(task_id), ["add", *targets])


def commit(task_id: str, message: str) -> Dict[str, Any]:
    msg = str(message or "").strip()
    if not msg:
        return {"ok": False, "error": "commit message required", "code": -1,
                "output": ""}
    return _git(_task_dir(task_id), ["commit", "-m", msg])


def run(task_id: str, action: str, **kwargs: Any) -> Dict[str, Any]:
    act = str(action or "status").strip().lower()
    if act in ("status", "log", "diff", "branch", "branches"):
        fn = {"status": status, "log": log, "diff": diff,
              "branch": branches, "branches": branches}[act]
        try:
            return fn(task_id, **kwargs)
        except TypeError:
            return fn(task_id)
    if act == "add":
        return add(task_id, kwargs.get("paths"))
    if act == "commit":
        return commit(task_id, kwargs.get("message", ""))
    if act == "init":
        return init(task_id)
    return {"ok": False, "error": f"unknown git action: {act}", "code": -1,
            "output": ""}