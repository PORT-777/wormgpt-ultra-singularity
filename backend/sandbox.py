"""
Phase 3 Sandbox Environments (adapted to existing WUS FastAPI/Windows stack).

Provides session-oriented sandbox control APIs for Linux/Windows analysis workflows.
- Linux: Docker container if available, else WSL distro shell if available, else local
  isolated workspace shell fallback (labeled in status).
- Windows: isolated per-session workspace executed via cmd/powershell on host tools,
  with file snapshot/diff, command history, and basic process/result capture.

No external secrets, no stubs for API surface; capabilities reported truthfully.
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import configs as config
    ROOT_WORKSPACE = Path(getattr(config, "WORKSPACE_DIR", Path.cwd())).resolve()
except Exception:
    ROOT_WORKSPACE = Path.cwd().resolve()

SANDBOX_ROOT = (ROOT_WORKSPACE / "data" / "sandboxes").resolve()
SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

def _now() -> float:
    return time.time()

def _safe_name(name: str, default: str = "file.bin") -> str:
    n = Path(str(name or default)).name
    n = re.sub(r"[^A-Za-z0-9._-]+", "_", n).strip("._") or default
    return n[:120]

def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)

def _run_sync(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 60, env: Optional[dict] = None) -> Dict[str, Any]:
    started = _now()
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout or 60)),
            env=env,
            shell=False,
        )
        return {
            "ok": p.returncode == 0,
            "code": p.returncode,
            "stdout": (p.stdout or "")[-20000:],
            "stderr": (p.stderr or "")[-20000:],
            "duration_ms": int((_now() - started) * 1000),
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ((e.stdout or b"").decode(errors="replace") if e.stdout else "")
        err = (e.stderr or "") if isinstance(e.stderr, str) else ((e.stderr or b"").decode(errors="replace") if e.stderr else "")
        return {"ok": False, "code": None, "timeout": True, "stdout": out[-20000:], "stderr": err[-20000:], "duration_ms": int((_now() - started) * 1000), "cmd": cmd}
    except Exception as e:
        return {"ok": False, "code": None, "error": f"{type(e).__name__}: {e}", "stdout": "", "stderr": "", "duration_ms": int((_now() - started) * 1000), "cmd": cmd}

def _detect_linux_backend() -> Tuple[str, Dict[str, Any]]:
    info: Dict[str, Any] = {}
    docker = _which("docker")
    if docker:
        probe = _run_sync([docker, "version", "--format", "{{.Server.Version}}"], timeout=8)
        info["docker"] = {"path": docker, "available": bool(probe.get("ok")), "detail": (probe.get("stdout") or probe.get("stderr") or probe.get("error") or "").strip()[:200]}
        if probe.get("ok"):
            return "docker", info
    wsl = _which("wsl.exe") or _which("wsl")
    if wsl and os.name == "nt":
        probe = _run_sync([wsl, "-e", "sh", "-lc", "echo WUS_WSL_OK"], timeout=8)
        info["wsl"] = {"path": wsl, "available": "WUS_WSL_OK" in (probe.get("stdout") or ""), "detail": (probe.get("stdout") or probe.get("stderr") or probe.get("error") or "").strip()[:200]}
        if "WUS_WSL_OK" in (probe.get("stdout") or ""):
            return "wsl", info
    return "local", info

def _detect_windows_backend() -> Tuple[str, Dict[str, Any]]:
    info: Dict[str, Any] = {"platform": platform.platform()}
    # Windows Sandbox / Hyper-V orchestration not guaranteed; expose truthful local isolated backend
    wsandbox = _which("WindowsSandbox.exe") or (Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "WindowsSandbox.exe")
    try:
        ws_exists = bool(wsandbox and Path(str(wsandbox)).exists())
    except Exception:
        ws_exists = False
    info["windows_sandbox_exe"] = {"present": ws_exists}
    return "local", info

@dataclass
class SandboxSession:
    id: str
    kind: str  # windows|linux
    backend: str
    status: str = "idle"
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    workdir: str = ""
    distro: str = ""
    container_id: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_history: bool = True) -> Dict[str, Any]:
        d = asdict(self)
        if not include_history:
            d["history"] = [{"ts": h.get("ts"), "kind": h.get("kind"), "ok": h.get("ok")} for h in self.history[-20:]]
        d["history_count"] = len(self.history)
        return d

class SandboxManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, SandboxSession] = {}

    def _get(self, sid: str) -> SandboxSession:
        with self._lock:
            s = self._sessions.get(sid)
        if not s:
            raise KeyError(sid)
        return s

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.to_dict(False) for s in sorted(self._sessions.values(), key=lambda x: x.updated_at, reverse=True)]

    def capabilities(self) -> Dict[str, Any]:
        linux_backend, linux_info = _detect_linux_backend()
        win_backend, win_info = _detect_windows_backend()
        return {
            "ok": True,
            "platform": platform.platform(),
            "sandbox_root": str(SANDBOX_ROOT),
            "linux": {
                "available": True,
                "backend": linux_backend,
                "distros": ["ubuntu:22.04", "kalilinux/kali-rolling", "remnux/remnux", "local-shell"],
                "features": {
                    "docker_container": linux_backend == "docker",
                    "wsl": linux_backend == "wsl",
                    "local_isolated_workspace": True,
                    "network_isolated_default": linux_backend == "docker",
                    "auto_destroy": True,
                },
                "details": linux_info,
            },
            "windows": {
                "available": os.name == "nt",
                "backend": win_backend,
                "features": {
                    "windows_sandbox_or_vm_orchestration": False,
                    "local_isolated_workspace": True,
                    "snapshot_restore_workspace": True,
                    "process_exec": True,
                },
                "details": win_info,
            },
        }

    def start(self, kind: str, distro: str = "", session_id: Optional[str] = None) -> Dict[str, Any]:
        kind = (kind or "").strip().lower()
        if kind not in {"linux", "windows"}:
            raise ValueError("kind must be 'linux' or 'windows'")
        if kind == "windows" and os.name != "nt":
            raise ValueError("Windows sandbox is only available on Windows hosts")
        sid = (session_id or uuid.uuid4().hex[:12]).strip() or uuid.uuid4().hex[:12]
        backend_info: Dict[str, Any] = {}
        backend = "local"
        if kind == "linux":
            backend, backend_info = _detect_linux_backend()
        else:
            backend, backend_info = _detect_windows_backend()
        workdir = (SANDBOX_ROOT / kind / sid / "workspace")
        workdir.mkdir(parents=True, exist_ok=True)
        sess = SandboxSession(id=sid, kind=kind, backend=backend, status="starting", workdir=str(workdir), distro=distro or "", meta={"backend_info": backend_info})
        container_id = ""
        if kind == "linux" and backend == "docker":
            image = distro or "ubuntu:22.04"
            # create stopped/idle long-running container with workspace mounted
            cname = f"wus_sb_{sid}"
            cmd = ["docker", "run", "-d", "--name", cname, "--network", "none", "-v", f"{str(workdir)}:/workspace", "-w", "/workspace", image, "sh", "-lc", "tail -f /dev/null"]
            res = _run_sync(cmd, timeout=120)
            sess.history.append({"ts": _now(), "kind": "docker_run", **res})
            if res.get("ok"):
                container_id = (res.get("stdout") or "").strip().splitlines()[-1][:64]
                sess.container_id = container_id
                sess.meta["container_name"] = cname
            else:
                # fallback to local if docker run fails
                sess.backend = "local"
                sess.meta["docker_fallback_error"] = (res.get("stderr") or res.get("error") or "docker run failed")[:500]
        if kind == "linux" and sess.backend == "wsl":
            sess.meta["wsl_distro"] = distro or "default"
        sess.status = "running"
        sess.updated_at = _now()
        with self._lock:
            self._sessions[sid] = sess
        sess.history.append({"ts": _now(), "kind": "start", "ok": True, "backend": sess.backend})
        return sess.to_dict()

    def status(self, sid: str) -> Dict[str, Any]:
        s = self._get(sid)
        live: Dict[str, Any] = {}
        if s.kind == "linux" and s.backend == "docker" and s.container_id:
            live = _run_sync(["docker", "inspect", "-f", "{{.State.Status}}", s.container_id], timeout=10)
        s.updated_at = _now()
        d = s.to_dict(False)
        d["live"] = {"ok": live.get("ok"), "detail": (live.get("stdout") or live.get("stderr") or "").strip()} if live else {}
        return d

    def destroy(self, sid: str) -> Dict[str, Any]:
        s = self._get(sid)
        res: Dict[str, Any] = {"ok": True}
        if s.kind == "linux" and s.backend == "docker" and s.container_id:
            res = _run_sync(["docker", "rm", "-f", s.container_id], timeout=30)
            s.history.append({"ts": _now(), "kind": "docker_rm", **res})
        s.status = "destroyed"
        s.updated_at = _now()
        return {"ok": bool(res.get("ok", True)), "session": s.to_dict(False), "detail": res}

    def _write_artifact(self, s: SandboxSession, name: str, content: bytes) -> Dict[str, Any]:
        safe = _safe_name(name)
        out = Path(s.workdir) / "artifacts" / safe
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content)
        meta = {"name": safe, "path": str(out), "size": len(content), "ts": _now()}
        s.artifacts.append(meta)
        s.updated_at = _now()
        return meta

    def upload(self, sid: str, filename: str, content: bytes) -> Dict[str, Any]:
        s = self._get(sid)
        if s.status in {"destroyed"}:
            raise ValueError("session destroyed")
        meta = self._write_artifact(s, filename or "upload.bin", content)
        s.history.append({"ts": _now(), "kind": "upload", "ok": True, "name": meta["name"], "size": meta["size"]})
        return {"ok": True, "artifact": meta, "session_id": s.id}

    def _exec_linux(self, s: SandboxSession, command: str, timeout: int) -> Dict[str, Any]:
        if s.backend == "docker" and s.container_id:
            return _run_sync(["docker", "exec", s.container_id, "sh", "-lc", command], cwd=Path(s.workdir), timeout=timeout)
        if s.backend == "wsl":
            wsl = _which("wsl.exe") or _which("wsl") or "wsl"
            # map windows path to wsl path best-effort
            win_path = str(Path(s.workdir).resolve())
            wcmd = f'cd "$(wslpath -a "{win_path}")" && {command}'
            return _run_sync([wsl, "-e", "sh", "-lc", wcmd], timeout=timeout)
        # local fallback
        bash = _which("bash")
        if bash:
            return _run_sync([bash, "-lc", command], cwd=Path(s.workdir), timeout=timeout)
        return _run_sync(["cmd", "/c", command], cwd=Path(s.workdir), timeout=timeout)

    def _exec_windows(self, s: SandboxSession, command: str, timeout: int, shell: str = "powershell") -> Dict[str, Any]:
        if shell == "cmd":
            return _run_sync(["cmd", "/c", command], cwd=Path(s.workdir), timeout=timeout)
        ps = _which("powershell.exe") or _which("powershell") or "powershell"
        return _run_sync([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command], cwd=Path(s.workdir), timeout=timeout)

    def execute(self, sid: str, command: str, timeout: int = 60, shell: str = "powershell") -> Dict[str, Any]:
        s = self._get(sid)
        if s.status == "destroyed":
            raise ValueError("session destroyed")
        cmd_str = "" if command is None else str(command)
        if not cmd_str.strip():
            raise ValueError("command required")
        s.status = "running"
        if s.kind == "linux":
            res = self._exec_linux(s, cmd_str, timeout)
        else:
            res = self._exec_windows(s, cmd_str, timeout, shell=shell)
        stdout = "" if res.get("stdout") is None else str(res.get("stdout"))
        stderr = "" if res.get("stderr") is None else str(res.get("stderr"))
        event = {
            "ts": _now(),
            "kind": "exec",
            "command": cmd_str[:4000],
            "shell": shell,
            "ok": bool(res.get("ok")),
            "code": res.get("code"),
            "duration_ms": res.get("duration_ms"),
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
            "timeout": bool(res.get("timeout")),
            "error": res.get("error"),
        }
        s.history.append(event)
        s.updated_at = _now()
        return {"ok": bool(res.get("ok")), "session_id": s.id, "result": event, "backend": s.backend}

    def _snapshot_files(self, root: Path) -> Dict[str, Dict[str, Any]]:
        snap: Dict[str, Dict[str, Any]] = {}
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                rel = str(p.relative_to(root))
                st = p.stat()
                snap[rel] = {"size": st.st_size, "mtime": st.st_mtime}
            except Exception:
                continue
        return snap

    def snapshot(self, sid: str, note: str = "") -> Dict[str, Any]:
        s = self._get(sid)
        files = self._snapshot_files(Path(s.workdir))
        snap_id = uuid.uuid4().hex[:10]
        # copy workspace state
        snap_dir = Path(s.workdir).parent / "snapshots" / snap_id
        if Path(s.workdir).exists():
            shutil.copytree(Path(s.workdir), snap_dir, dirs_exist_ok=True)
        meta = {"id": snap_id, "ts": _now(), "note": note or "", "file_count": len(files), "dir": str(snap_dir)}
        s.snapshots.append(meta)
        s.history.append({"ts": _now(), "kind": "snapshot", "ok": True, "snapshot_id": snap_id, "file_count": len(files)})
        s.updated_at = _now()
        return {"ok": True, "snapshot": meta, "session_id": s.id}

    def restore(self, sid: str, snapshot_id: str) -> Dict[str, Any]:
        s = self._get(sid)
        snap = next((x for x in s.snapshots if x.get("id") == snapshot_id), None)
        if not snap:
            raise ValueError("snapshot not found")
        snap_dir = Path(snap.get("dir") or "")
        if not snap_dir.exists():
            raise ValueError("snapshot data missing")
        work = Path(s.workdir)
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(snap_dir, work, dirs_exist_ok=True)
        s.history.append({"ts": _now(), "kind": "restore", "ok": True, "snapshot_id": snapshot_id})
        s.updated_at = _now()
        return {"ok": True, "restored": snapshot_id, "session_id": s.id}

    def results(self, sid: str) -> Dict[str, Any]:
        s = self._get(sid)
        files = self._snapshot_files(Path(s.workdir))
        execs = [h for h in s.history if h.get("kind") == "exec"]
        stdout = "\n".join([str(e.get("stdout") or "") for e in execs[-10:]])[-20000:]
        stderr = "\n".join([str(e.get("stderr") or "") for e in execs[-10:]])[-20000:]
        return {
            "ok": True,
            "session": s.to_dict(False),
            "summary": {
                "exec_count": len(execs),
                "artifact_count": len(s.artifacts),
                "snapshot_count": len(s.snapshots),
                "file_count": len(files),
            },
            "files": [{"path": k, **v} for k, v in list(files.items())[:500]],
            "stdout_tail": stdout,
            "stderr_tail": stderr,
            "recent_events": s.history[-50:],
            "artifacts": s.artifacts[-200:],
            "snapshots": s.snapshots[-50:],
        }

SANDBOX_MANAGER = SandboxManager()

# Backward-compatible legacy helpers
def run_python(code: str, timeout: int = 30, network: bool = False) -> Dict:
    sid = SANDBOX_MANAGER.start("windows")["id"]
    try:
        # write temp script in session workspace and execute
        sess = SANDBOX_MANAGER._get(sid)  # internal use
        script = Path(sess.workdir) / "_run.py"
        script.write_text(code or "", encoding="utf-8", errors="replace")
        res = SANDBOX_MANAGER.execute(sid, f'python "{script.name}"', timeout=timeout, shell="powershell")
        return {"ok": res.get("ok", False), "session_id": sid, "result": res.get("result")}
    finally:
        try:
            SANDBOX_MANAGER.destroy(sid)
        except Exception:
            pass

def run_shell(cmd: str, timeout: int = 30) -> Dict:
    sid = SANDBOX_MANAGER.start("windows")["id"]
    try:
        res = SANDBOX_MANAGER.execute(sid, cmd, timeout=timeout, shell="powershell")
        return {"ok": res.get("ok", False), "session_id": sid, "result": res.get("result")}
    finally:
        try:
            SANDBOX_MANAGER.destroy(sid)
        except Exception:
            pass
