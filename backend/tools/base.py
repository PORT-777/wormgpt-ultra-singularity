"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Modular, extensible tool library.

Every tool is an independent class here. Adding one = drop a file in
this package with a `Tool` subclass; the registry auto-discovers it.

Access control lives in this module:
- A per-run `contextvars` token full_access flag is set *per run* by the
  agent engine (which gets it from the user's explicit request). Tools that
  touch
  the host (UniversalFileManager host-scope, SystemCommander) check it
  and refuse otherwise.
"""
from __future__ import annotations

import contextvars
from pathlib import Path
import re
from abc import ABC, abstractmethod
from typing import Any, Dict

import configs as config

# ------------------------------------------------------------------ #
#  Per-run access context (set by agent_engine before each run).
#  contextvars -> every concurrent request/task gets its OWN value;
#  the previous module-global dict leaked God-mode between users.
# ------------------------------------------------------------------ #
_FULL_ACCESS: contextvars.ContextVar = contextvars.ContextVar(
    "🔥😈 PORT 777 EVIL ☠️🔥👹_full_access", default=False
)
_CKPT_CTX: contextvars.ContextVar = contextvars.ContextVar(
    "🔥😈 PORT 777 EVIL ☠️🔥👹_ckpt_ctx", default=None
)


def set_full_access(enabled: bool) -> None:
    _FULL_ACCESS.set(bool(enabled))


def full_access() -> bool:
    return _FULL_ACCESS.get()


def set_checkpoint_context(ctx: Dict[str, Any] | None) -> None:
    _CKPT_CTX.set(ctx)


def checkpoint_context() -> Dict[str, Any] | None:
    v = _CKPT_CTX.get()
    return v if isinstance(v, dict) else None


def _active_workspace() -> str | None:
    """Path of the current execution task workspace, if any."""
    try:
        import execution

        return execution.active_workspace()
    except Exception:
        return None


class Tool(ABC):
    """Base class for every agent tool."""

    name: str = "base_tool"
    description: str = "abstract base tool"
    example: Dict[str, Any] = {}

    @abstractmethod
    async def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a string observation."""

    # ------------------------- sandboxing helpers --------------------- #
    @staticmethod
    def safe_path(path: str) -> "Path":  # noqa: F821
        """Resolve a path inside the active workspace (blocks traversal).

        When an execution task is active, the task's private workspace is used
        instead of the global workspace, so a task can never touch another
        task's files."""
        root = Path(_active_workspace() or config.WORKSPACE_DIR).resolve()
        target = (root / str(path).lstrip("/\\")).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"path '{path}' escapes the workspace sandbox")
        return target

    @staticmethod
    def resolve_any(path: str):
        """
        Full-Access-mode path resolution: ANY path on the host is allowed,
        *except* OS-critical zones that could brick a machine or tamper
        with system boot/persistence. This is deliberately denylist-based:
        the user owns the machine, but nobody should be able to (even
        accidentally) command rm -rf C:\\Windows.
        """
        root = Path(_active_workspace() or config.WORKSPACE_DIR)
        target = Path(str(path)).expanduser().resolve()
        # sandboxed relative paths still resolve into the workspace
        if not target.is_absolute():
            target = (root / str(path).lstrip("/\\")).resolve()

        return target


def get_schema(tool: Tool) -> str:
        return target


def get_schema(tool: Tool) -> str:
    """Compact tool spec injected into the agent's system prompt."""
    return (
        f"- {tool.name}: {tool.description}\n"
        f"  Input JSON example: {tool.example}"
    )
