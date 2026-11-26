"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Workspace Manager
Core logic for local directory management — attach, explore, read, write, and execute
within operator-owned project directories.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging

log = logging.getLogger("workspace_manager")


class WorkspaceManager:
    """
    Manages attached workspace directories for the Engineer Mode agent.
    Provides sandboxed file operations and command execution within attached projects.
    """

    # Heavy directories are never counted: on a large repo node_modules/.git
    # can exceed hundreds of thousands of files and block attach for minutes.
    _COUNT_SKIP_DIRS = {
        ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env",
        "__pycache__", "dist", "build", "target", "out", ".next",
        ".pytest_cache", ".mypy_cache", ".ruff_cache", "tdata",
    }

    def __init__(self):
        self._workspaces: Dict[str, Path] = {}
        self._lock = threading.Lock()                       # guards _workspaces / _ws_locks
        self._ws_locks: Dict[str, threading.RLock] = {}     # per-workspace reentrant locks
        self._locked_workspaces: set = set()                # explicitly locked workspace IDs
        self._audit_log: List[Dict[str, Any]] = []
        self._snapshots: Dict[str, List[Dict[str, Any]]] = {}  # ws_id -> [snapshot entries]
        self._file_counts: Dict[str, int] = {}              # cached, pruned file counts

    def _count_files(self, root: Path, limit: int = 500_000) -> int:
        """Count files while skipping dependency/VCS dirs. O(code files)."""
        total = 0
        stack = [str(root)]
        while stack and total < limit:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                if entry.name in self._COUNT_SKIP_DIRS:
                                    continue
                                stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                total += 1
                                if total >= limit:
                                    break
                        except OSError:
                            continue
            except OSError:
                continue
        return total

    def attach_workspace(self, workspace_id: str, path: str) -> Dict[str, Any]:
        """
        Attach a local directory as a workspace.
        Returns workspace info including resolved path and file count.
        """
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            return {"error": f"Directory not found: {path}"}

        with self._lock:
            self._workspaces[workspace_id] = resolved

        file_count = self._count_files(resolved)
        self._file_counts[workspace_id] = file_count
        self._audit("attach", workspace_id, str(resolved), {"file_count": file_count})

        return {
            "workspace_id": workspace_id,
            "path": str(resolved),
            "file_count": file_count,
            "status": "attached",
        }

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all attached workspaces."""
        with self._lock:
            result = []
            for ws_id, ws_path in self._workspaces.items():
                file_count = self._file_counts.get(ws_id)
                if file_count is None:
                    file_count = self._count_files(ws_path)
                    self._file_counts[ws_id] = file_count
                result.append({
                    "workspace_id": ws_id,
                    "path": str(ws_path),
                    "file_count": file_count,
                })
            return result

    def detach_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Detach a workspace by ID."""
        with self._lock:
            if workspace_id not in self._workspaces:
                return {"error": f"Workspace not found: {workspace_id}"}
            path = str(self._workspaces.pop(workspace_id))
            self._file_counts.pop(workspace_id, None)

        self._audit("detach", workspace_id, path, {})
        return {"workspace_id": workspace_id, "path": path, "status": "detached"}

    def _resolve_path(self, workspace_id: str, relative_path: str) -> Path:
        """Resolve a relative path within a workspace, blocking traversal."""
        with self._lock:
            if workspace_id not in self._workspaces:
                raise ValueError(f"Workspace not found: {workspace_id}")
            base = self._workspaces[workspace_id]

        target = (base / relative_path.lstrip("/\\")).resolve()
        if base != target and base not in target.parents:
            raise ValueError(f"Path '{relative_path}' escapes workspace sandbox")
        return target

    def _ws_lock_for(self, workspace_id: str) -> threading.RLock:
        """Get (creating if needed) a reentrant lock for a specific workspace."""
        with self._lock:
            if workspace_id not in self._ws_locks:
                self._ws_locks[workspace_id] = threading.RLock()
            return self._ws_locks[workspace_id]

    # ------------------------------------------------------------------ #
    #  Project-level locking
    # ------------------------------------------------------------------ #
    def lock_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Explicitly lock a workspace so only one operation runs at a time."""
        with self._lock:
            if workspace_id not in self._workspaces:
                return {"error": f"Workspace not found: {workspace_id}"}
            if workspace_id in self._locked_workspaces:
                return {"workspace_id": workspace_id, "status": "already_locked"}
            self._locked_workspaces.add(workspace_id)
        self._audit("lock_workspace", workspace_id, str(self._workspaces[workspace_id]), {})
        return {"workspace_id": workspace_id, "status": "locked"}

    def unlock_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Unlock a previously locked workspace."""
        with self._lock:
            if workspace_id not in self._locked_workspaces:
                return {"workspace_id": workspace_id, "status": "not_locked"}
            self._locked_workspaces.discard(workspace_id)
        self._audit("unlock_workspace", workspace_id, "", {})
        return {"workspace_id": workspace_id, "status": "unlocked"}

    def is_locked(self, workspace_id: str) -> bool:
        """Check whether a workspace is explicitly locked."""
        with self._lock:
            return workspace_id in self._locked_workspaces

    # ------------------------------------------------------------------ #
    #  Snapshotting (automatic backups before edits)
    # ------------------------------------------------------------------ #
    def create_snapshot(self, workspace_id: str, label: str = "") -> Dict[str, Any]:
        """
        Create a snapshot of the entire workspace: copy all files into
        data/snapshots/<workspace_id>/<snapshot_id>/.
        Returns the snapshot id.
        """
        try:
            target = self._resolve_path(workspace_id, ".")
        except ValueError as exc:
            return {"error": str(exc)}

        snap_root = Path("data") / "snapshots" / workspace_id
        snap_root.mkdir(parents=True, exist_ok=True)
        snap_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:17]
        snap_dir = snap_root / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        file_count = 0
        for f in target.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts:
                rel = f.relative_to(target)
                dest = snap_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                file_count += 1

        entry = {
            "id": snap_id,
            "label": label or f"snapshot-{snap_id}",
            "ts": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "workspace_id": workspace_id,
            "path": str(target),
            "file_count": file_count,
            "dir": str(snap_dir),
        }
        self._snapshots.setdefault(workspace_id, []).append(entry)
        self._audit("create_snapshot", workspace_id, str(target), {
            "snapshot_id": snap_id, "file_count": file_count, "label": label,
        })
        return {"workspace_id": workspace_id, "snapshot_id": snap_id,
                "label": entry["label"], "file_count": file_count, "status": "created"}

    def list_snapshots(self, workspace_id: str) -> Dict[str, Any]:
        """List all snapshots for a workspace."""
        snaps = self._snapshots.get(workspace_id, [])
        # Also include snapshots persisted on disk
        snap_root = Path("data") / "snapshots" / workspace_id
        if snap_root.exists():
            for d in sorted(snap_root.iterdir()):
                if d.is_dir() and not any(s["id"] == d.name for s in snaps):
                    snaps.append({
                        "id": d.name,
                        "label": f"disk-snapshot-{d.name}",
                        "ts": "",
                        "workspace_id": workspace_id,
                        "file_count": sum(1 for _ in d.rglob("*") if _.is_file()),
                        "dir": str(d),
                    })
        return {"workspace_id": workspace_id, "snapshots": snaps}

    def restore_snapshot(self, workspace_id: str, snapshot_id: str) -> Dict[str, Any]:
        """Restore a workspace from a snapshot (overwrites current files)."""
        try:
            target = self._resolve_path(workspace_id, ".")
        except ValueError as exc:
            return {"error": str(exc)}

        # Find the snapshot dir
        snap_dir = None
        for s in self._snapshots.get(workspace_id, []):
            if s["id"] == snapshot_id:
                snap_dir = Path(s["dir"])
                break
        if snap_dir is None or not snap_dir.exists():
            cand = Path("data") / "snapshots" / workspace_id / snapshot_id
            if cand.exists():
                snap_dir = cand
        if snap_dir is None or not snap_dir.exists():
            return {"error": f"Snapshot not found: {snapshot_id}"}

        restored = 0
        for f in snap_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(snap_dir)
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                restored += 1

        self._audit("restore_snapshot", workspace_id, str(target), {
            "snapshot_id": snapshot_id, "restored": restored,
        })
        return {"workspace_id": workspace_id, "snapshot_id": snapshot_id,
                "restored": restored, "status": "restored"}

    def list_files(self, workspace_id: str, directory: str = ".") -> Dict[str, Any]:
        """List files and directories within a workspace."""
        try:
            target = self._resolve_path(workspace_id, directory)
            if not target.exists() or not target.is_dir():
                return {"error": f"Directory not found: {directory}"}

            items = []
            for item in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                })

            self._audit("list_files", workspace_id, str(target), {"count": len(items)})
            return {"workspace_id": workspace_id, "directory": directory, "items": items}

        except Exception as e:
            log.error(f"list_files error: {e}")
            return {"error": str(e)}

    def read_file(self, workspace_id: str, file_path: str) -> Dict[str, Any]:
        """Read a file from within a workspace."""
        try:
            target = self._resolve_path(workspace_id, file_path)
            if not target.exists() or not target.is_file():
                return {"error": f"File not found: {file_path}"}

            content = target.read_text(encoding="utf-8", errors="replace")
            self._audit("read_file", workspace_id, str(target), {"size": len(content)})
            return {"workspace_id": workspace_id, "file": file_path, "content": content}

        except Exception as e:
            log.error(f"read_file error: {e}")
            return {"error": str(e)}

    def write_file(self, workspace_id: str, file_path: str, content: str) -> Dict[str, Any]:
        """Write content to a file within a workspace (creates or overwrites)."""
        try:
            target = self._resolve_path(workspace_id, file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

            self._audit("write_file", workspace_id, str(target), {"size": len(content)})
            return {"workspace_id": workspace_id, "file": file_path, "status": "written", "size": len(content)}

        except Exception as e:
            log.error(f"write_file error: {e}")
            return {"error": str(e)}

    def edit_file(self, workspace_id: str, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Dict[str, Any]:
        """Perform targeted text replacement within a file."""
        try:
            target = self._resolve_path(workspace_id, file_path)
            if not target.exists() or not target.is_file():
                return {"error": f"File not found: {file_path}"}

            content = target.read_text(encoding="utf-8")
            if old_string not in content:
                return {"error": f"String not found in file: {old_string}"}

            if replace_all:
                count = content.count(old_string)
                new_content = content.replace(old_string, new_string)
            else:
                count = 1
                new_content = content.replace(old_string, new_string, 1)

            target.write_text(new_content, encoding="utf-8")
            self._audit("edit_file", workspace_id, str(target), {"replacements": count})
            return {"workspace_id": workspace_id, "file": file_path, "status": "edited", "replacements": count}

        except Exception as e:
            log.error(f"edit_file error: {e}")
            return {"error": str(e)}

    def execute_command(self, workspace_id: str, command: str, cwd: str = ".") -> Dict[str, Any]:
        """Execute a shell command within a workspace directory."""
        try:
            target = self._resolve_path(workspace_id, cwd)
            if not target.exists() or not target.is_dir():
                return {"error": f"Directory not found: {cwd}"}

            result = subprocess.run(
                command,
                shell=True,
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=120,
            )

            self._audit("execute_command", workspace_id, str(target), {
                "command": command,
                "returncode": result.returncode,
            })

            return {
                "workspace_id": workspace_id,
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Command timed out after 120 seconds"}
        except Exception as e:
            log.error(f"execute_command error: {e}")
            return {"error": str(e)}

    def get_tree(self, workspace_id: str, directory: str = ".", max_depth: int = 3) -> Dict[str, Any]:
        """Generate a tree-like structure of the workspace directory."""
        try:
            target = self._resolve_path(workspace_id, directory)
            if not target.exists() or not target.is_dir():
                return {"error": f"Directory not found: {directory}"}

            ignore_dirs = set(self._COUNT_SKIP_DIRS)
            lines = []
            self._build_tree(target, "", 0, max_depth, ignore_dirs, lines)

            self._audit("get_tree", workspace_id, str(target), {"depth": max_depth, "lines": len(lines)})
            return {"workspace_id": workspace_id, "directory": directory, "tree": "\n".join(lines)}

        except Exception as e:
            log.error(f"get_tree error: {e}")
            return {"error": str(e)}

    def _build_tree(self, path: Path, prefix: str, depth: int, max_depth: int, ignore_dirs: set, lines: List[str]):
        if depth > max_depth:
            return
        try:
            items = sorted(list(path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        except Exception:
            return

        # Filter before computing connectors so the last visible entry renders
        # with a closing corner even when ignored dirs are skipped.
        items = [it for it in items if it.name not in ignore_dirs]
        count = len(items)
        for i, item in enumerate(items):
            is_last = (i == count - 1)
            connector = "└── " if is_last else "├── "

            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._build_tree(item, new_prefix, depth + 1, max_depth, ignore_dirs, lines)
            else:
                lines.append(f"{prefix}{connector}{item.name}")

    def _audit(self, action: str, workspace_id: str, path: str, meta: Dict[str, Any]):
        """Record an audit entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "action": action,
            "workspace_id": workspace_id,
            "path": path,
            "meta": meta,
        }
        self._audit_log.append(entry)
        # Also write to audit.jsonl
        try:
            audit_file = Path("data/audit.jsonl")
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Never break execution on audit failure


# Singleton instance
workspace_manager = WorkspaceManager()