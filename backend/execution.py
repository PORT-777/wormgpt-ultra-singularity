"""
Universal Execution Engine
==========================
One task model, many environments:

  local      -> the Windows/Linux host this backend runs on
  cloud      -> an isolated server-side workspace (same code, per-task dir)
  upload     -> a workspace created from uploaded files / a ZIP project
  sandbox    -> isolated per-task workspace (+ optional Docker/WSL shell)
  kali       -> only when runtime_env verifies /etc/os-release ID=kali
  android    -> only when a real Android/Termux runtime is detected

Every task owns a private directory:

  <workspace>/data/exec/tasks/<task_id>/
      workspace/        <- the agent's cwd (never the whole disk)
      task.json         <- status, events, artifacts
      .exec/            <- helper scripts, logs

Real execution only: subprocesses with captured stdout/stderr, timeouts,
process-tree cancellation, risk classification, path-traversal-safe ZIP
extraction and atomic JSON persistence.  No simulated outputs anywhere.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import configs as config
    WORKSPACE_DIR = Path(getattr(config, "WORKSPACE_DIR", Path.cwd())).resolve()
except Exception:  # pragma: no cover
    WORKSPACE_DIR = Path.cwd().resolve()

import runtime_env

EXEC_ROOT = (WORKSPACE_DIR / "data" / "exec").resolve()
TASKS_DIR = EXEC_ROOT / "tasks"
ARCHIVES_DIR = EXEC_ROOT / "archives"
EXEC_ROOT.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)

MAX_OUTPUT = 20000
MAX_FILES = 5000
MAX_EXTRACT_BYTES = 500 * 1024 * 1024  # 500 MB uncompressed per archive
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
DEFAULT_TIMEOUT = 120

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".pytest_cache", ".mypy_cache", ".exec"}

# task id -> live subprocess (never persisted)
_PROCS: Dict[str, Any] = {}
_PROC_LOCK = __import__("threading").Lock()

# per-run active task (used by agent tools)
_ACTIVE_TASK: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("exec_active_task", default=None)


class EnvironmentUnavailable(RuntimeError):
    """Raised when the requested environment genuinely cannot run here."""

    def __init__(self, requested: str, reason: str, available: Optional[List[Dict[str, Any]]] = None):
        super().__init__(reason)
        self.requested = requested
        self.reason = reason
        self.available = available or []


# --------------------------------------------------------------------------- #
#  persistence helpers
# --------------------------------------------------------------------------- #
def _now() -> float:
    return time.time()


def _atomic_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _task_file(tid: str) -> Path:
    return TASKS_DIR / f"{tid}.json"


def _task_dir(tid: str) -> Path:
    return TASKS_DIR / tid


def _workdir(tid: str) -> Path:
    return _task_dir(tid) / "workspace"


def load_task(tid: str) -> Optional[Dict[str, Any]]:
    if not _valid_tid(tid):
        return None
    try:
        return json.loads(_task_file(tid).read_text(encoding="utf-8"))
    except Exception:
        return None


def save_task(task: Dict[str, Any]) -> None:
    if not _valid_tid(task.get("id", "")):
        raise ValueError("invalid task id")
    task["updated_at"] = _now()
    _atomic_json(_task_file(task["id"]), task)


def _event(task: Dict[str, Any], kind: str, message: str = "", **data: Any) -> None:
    ev = {"ts": _now(), "kind": kind, "message": message}
    ev.update(data)
    task.setdefault("events", []).append(ev)
    # keep the log bounded but useful
    if len(task["events"]) > 800:
        del task["events"][:200]
    save_task(task)


def public_task(task: Dict[str, Any]) -> Dict[str, Any]:
    t = {k: v for k, v in task.items() if not k.startswith("_") and k != "fingerprint"}
    t["events"] = task.get("events", [])[-80:]
    t["workdir"] = str(task.get("workdir") or "")
    return t


def _valid_tid(tid: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(tid or "")))


# --------------------------------------------------------------------------- #
#  environment resolution
# --------------------------------------------------------------------------- #
def _env_labels() -> Dict[str, str]:
    return {
        "auto": "Auto detect",
        "local": "Local machine",
        "windows": "Windows host",
        "linux": "Linux host",
        "kali": "Kali Linux",
        "wsl": "WSL",
        "android": "Android / Termux",
        "cloud": "Cloud / server workspace",
        "upload": "Uploaded project workspace",
        "sandbox": "Isolated sandbox",
    }


def resolve_environment(requested: str = "auto") -> Dict[str, Any]:
    """Pick a *real* environment.  Raises EnvironmentUnavailable with the exact
    missing runtime instead of silently falling back."""
    req = str(requested or "auto").strip().lower()
    fp = runtime_env.fingerprint()
    os_i = fp["os"]
    caps = fp["capabilities"]
    available = runtime_env.available_environments()
    labels = _env_labels()

    def unavailable(reason: str):
        raise EnvironmentUnavailable(req, reason, available)

    if req in ("", "auto"):
        if os_i.get("family") == "windows":
            env, detail = "windows", "host is Windows"
        elif os_i.get("family") == "android":
            env, detail = "android", "host is Android"
        elif os_i.get("family") == "linux":
            env, detail = "linux", os_i.get("distro_name") or "host is Linux"
        else:
            env, detail = "cloud", "server-side workspace"
        return {"env": env, "label": labels.get(env, env), "detail": detail,
                "isolated": env in ("cloud", "sandbox"), "fingerprint": runtime_env.summary()}

    if req in ("cloud", "upload", "sandbox"):
        return {"env": "cloud" if req != "sandbox" else "sandbox",
                "label": labels.get(req, req),
                "detail": "isolated server-side workspace",
                "isolated": True, "fingerprint": runtime_env.summary()}

    if req in ("local", "windows"):
        if os_i.get("family") != "windows":
            unavailable("local/Windows execution requires a Windows host; this runtime is "
                        f"{os_i.get('family') or 'unknown'} ({fp['runtime']['type']}).")
        return {"env": "windows", "label": labels["windows"],
                "detail": f"{os_i.get('name')} {os_i.get('version')} {os_i.get('arch') or ''}".strip(),
                "isolated": False, "fingerprint": runtime_env.summary()}

    if req == "linux":
        if os_i.get("family") != "linux":
            unavailable("Linux execution requires a Linux host (bare metal, WSL or container).")
        return {"env": "linux", "label": os_i.get("distro_name") or "Linux",
                "detail": f"{os_i.get('distro_name')} {os_i.get('distro_version')} · kernel {os_i.get('kernel')}",
                "isolated": False, "fingerprint": runtime_env.summary()}

    if req == "kali":
        if not os_i.get("is_kali"):
            unavailable("Kali is NOT available: /etc/os-release ID is "
                        f"{os_i.get('distro_id') or os_i.get('family')!r}, not 'kali'. "
                        "A standard Linux container is not Kali and Kali tools are not assumed.")
        return {"env": "kali", "label": "Kali Linux",
                "detail": f"verified {os_i.get('name')} {os_i.get('distro_version')}",
                "isolated": False, "fingerprint": runtime_env.summary()}

    if req == "wsl":
        if not os_i.get("is_wsl"):
            unavailable("WSL is not active on this host (kernel does not contain 'microsoft').")
        return {"env": "wsl", "label": "WSL", "detail": os_i.get("name") or "WSL",
                "isolated": False, "fingerprint": runtime_env.summary()}

    if req == "android":
        if os_i.get("family") != "android":
            unavailable("No Android runtime detected: backend is not running inside Android/Termux. "
                        "A browser on a phone cannot execute device commands.")
        return {"env": "android", "label": "Android / Termux",
                "detail": "Termux" if os_i.get("termux") else "Android host",
                "isolated": False, "fingerprint": runtime_env.summary()}

    unavailable(f"unknown environment {req!r}")


# --------------------------------------------------------------------------- #
#  task lifecycle
# --------------------------------------------------------------------------- #
def create_task(env: str = "auto", session_id: Optional[str] = None,
                owner: str = "local", title: str = "",
                approved: bool = False) -> Dict[str, Any]:
    resolved = resolve_environment(env)
    tid = uuid.uuid4().hex[:12]
    wd = _workdir(tid)
    (wd / ".exec").mkdir(parents=True, exist_ok=True)
    task = {
        "id": tid,
        "owner": owner,
        "session_id": session_id,
        "env": resolved["env"],
        "requested_env": env,
        "env_label": resolved["label"],
        "env_detail": resolved["detail"],
        "isolated": bool(resolved["isolated"]),
        "title": title or "execution task",
        "status": "created",
        "workdir": str(wd),
        "created_at": _now(),
        "updated_at": _now(),
        "started_at": None,
        "finished_at": None,
        "events": [],
        "artifacts": [],
        "project": {},
        "result": None,
        "error": None,
        "exit_code": None,
        "risk": "safe",
        "approved": bool(approved),
        "fingerprint": resolved["fingerprint"],
    }
    task["project"] = inspect_project(wd)
    save_task(task)
    _event(task, "created", f"task created on {resolved['label']}", env=resolved["env"])
    return public_task(task)


def get_task(tid: str) -> Optional[Dict[str, Any]]:
    return load_task(tid)


def list_tasks(owner: Optional[str] = None, session_id: Optional[str] = None,
               limit: int = 50) -> List[Dict[str, Any]]:
    out = []
    for f in sorted(TASKS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if owner and t.get("owner") != owner:
            continue
        if session_id and t.get("session_id") != session_id:
            continue
        out.append(public_task(t))
        if len(out) >= limit:
            break
    return out


def delete_task(tid: str) -> bool:
    t = load_task(tid)
    if t and t.get("status") == "running":
        cancel(tid)
    shutil.rmtree(_task_dir(tid), ignore_errors=True)
    for p in (ARCHIVES_DIR / f"{tid}.zip", ARCHIVES_DIR / f"{tid}.tar.gz"):
        try:
            p.unlink()
        except Exception:
            pass
    try:
        _task_file(tid).unlink()
    except Exception:
        pass
    return True


# --------------------------------------------------------------------------- #
#  project inspection
# --------------------------------------------------------------------------- #
_MARKERS = [
    ("package.json", "node", "npm"),
    ("requirements.txt", "python", "pip"),
    ("pyproject.toml", "python", "pip"),
    ("setup.py", "python", "pip"),
    ("Cargo.toml", "rust", "cargo"),
    ("go.mod", "go", "go"),
    ("pom.xml", "java", "maven"),
    ("build.gradle", "java", "gradle"),
    ("*.sln", "dotnet", "dotnet"),
    ("*.csproj", "dotnet", "dotnet"),
    ("Dockerfile", "docker", "docker"),
    ("Makefile", "make", "make"),
    ("composer.json", "php", "composer"),
    ("Gemfile", "ruby", "bundler"),
]

_ENTRYPOINTS = ("main.py", "app.py", "manage.py", "index.js", "server.js", "main.js",
                "main.go", "main.rs", "Program.cs", "Makefile", "docker-compose.yml")


def _match(root: Path, pattern: str) -> Optional[Path]:
    if "*" in pattern or "?" in pattern:
        try:
            return next(root.glob(pattern), None)
        except Exception:
            return None
    p = root / pattern
    return p if p.exists() else None


def inspect_project(workdir: str | Path) -> Dict[str, Any]:
    root = Path(workdir)
    found: List[Dict[str, Any]] = []
    if root.exists():
        for pattern, tech, pm in _MARKERS:
            p = _match(root, pattern)
            if p:
                found.append({"marker": pattern, "technology": tech, "package_manager": pm, "path": p.name})
        # one level deep for common project folders
        try:
            for child in root.iterdir():
                if not child.is_dir() or child.name in _SKIP_DIRS or child.name.startswith("."):
                    continue
                for pattern, tech, pm in _MARKERS:
                    p = _match(child, pattern)
                    if p:
                        found.append({"marker": pattern, "technology": tech, "package_manager": pm,
                                      "path": f"{child.name}/{p.name}"})
                        break
        except Exception:
            pass
    techs = sorted({f["technology"] for f in found})
    entries = [name for name in _ENTRYPOINTS if (root / name).exists()]
    return {"technologies": techs, "package_managers": sorted({f["package_manager"] for f in found}),
            "markers": found, "entrypoints": entries, "workdir": str(root)}


def _count_files(root: Path) -> int:
    n = 0
    for p in root.rglob("*"):
        if p.is_file():
            n += 1
            if n > MAX_FILES:
                break
    return n


# --------------------------------------------------------------------------- #
#  safe paths + file ops
# --------------------------------------------------------------------------- #
def _safe_join(tid: str, rel: str) -> Path:
    wd = _workdir(tid).resolve()
    rel = str(rel or "").replace("\\", "/").lstrip("/")
    target = (wd / rel).resolve()
    if target != wd and wd not in target.parents:
        raise ValueError(f"path escapes task workspace: {rel}")
    return target


def task_file_path(tid: str, rel: str) -> Path:
    """Resolve a real, existing file inside the task workspace (downloads)."""
    p = _safe_join(tid, rel)
    if not p.is_file():
        raise FileNotFoundError(rel)
    return p


def task_dir_path(tid: str) -> Path:
    """Task workspace root (used for downloads of directories)."""
    return _workdir(tid)


def list_files(tid: str) -> Dict[str, Any]:
    wd = _workdir(tid)
    items: List[Dict[str, Any]] = []
    if not wd.exists():
        return {"task_id": tid, "files": [], "count": 0}
    for p in sorted(wd.rglob("*")):
        try:
            rel = p.relative_to(wd)
        except Exception:
            continue
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        if p.is_dir():
            items.append({"path": str(rel).replace("\\", "/"), "is_dir": True, "size": 0})
        else:
            try:
                items.append({"path": str(rel).replace("\\", "/"), "is_dir": False,
                              "size": p.stat().st_size, "modified": p.stat().st_mtime})
            except Exception:
                continue
        if len(items) > MAX_FILES:
            break
    return {"task_id": tid, "files": items, "count": len(items), "project": inspect_project(wd)}


def read_file(tid: str, rel: str, max_bytes: int = 200_000) -> Dict[str, Any]:
    p = _safe_join(tid, rel)
    if not p.is_file():
        raise FileNotFoundError(rel)
    size = p.stat().st_size
    data = p.read_bytes()[:max_bytes]
    if b"\x00" in data[:4096]:
        return {"task_id": tid, "path": rel, "size": size, "binary": True, "content": ""}
    return {"task_id": tid, "path": rel, "size": size, "binary": False,
            "content": data.decode("utf-8", errors="replace")}


def write_file(tid: str, rel: str, content: str) -> Dict[str, Any]:
    p = _safe_join(tid, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content or "", encoding="utf-8")
    t = load_task(tid)
    if t:
        _event(t, "file_write", f"wrote {rel}", path=rel, bytes=len(content or ""))
        t["project"] = inspect_project(_workdir(tid))
        save_task(t)
    return {"task_id": tid, "path": rel, "written": len(content or "")}


def delete_path(tid: str, rel: str) -> Dict[str, Any]:
    p = _safe_join(tid, rel)
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    elif p.exists():
        p.unlink()
    t = load_task(tid)
    if t:
        _event(t, "file_delete", f"deleted {rel}", path=rel)
    return {"task_id": tid, "deleted": rel}


# --------------------------------------------------------------------------- #
#  upload / archive import
# --------------------------------------------------------------------------- #
_ARCHIVE_EXT = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"}


def _safe_archive_name(name: str) -> str:
    n = Path(str(name or "upload.bin")).name
    n = re.sub(r"[^A-Za-z0-9._-]+", "_", n).strip("._")
    return (n or "upload.bin")[:120]


def _valid_zip_member(info: zipfile.ZipInfo) -> bool:
    name = info.filename.replace("\\", "/")
    if not name or name.startswith("/") or ":" in name:
        return False
    if any(part in ("..", "") for part in name.split("/")[:-1]):
        return False
    # reject symlinks (unix mode high bits)
    mode = (info.external_attr >> 16) & 0o170000
    if mode == 0o120000:
        return False
    return True


def safe_extract_zip(zip_path: str | Path, dest: str | Path, strip_common_root: bool = True) -> Dict[str, Any]:
    """Extract a ZIP into *dest* with traversal/symlink/size protection."""
    zp = Path(zip_path)
    dest = Path(dest)
    if not zp.is_file():
        raise FileNotFoundError(str(zp))
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    count = 0
    with zipfile.ZipFile(zp) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        for info in infos:
            if not _valid_zip_member(info):
                raise ValueError(f"unsafe archive member rejected: {info.filename}")
        strip = ""
        if strip_common_root and infos:
            tops = {i.filename.replace("\\", "/").split("/")[0] for i in infos}
            if len(tops) == 1 and all("/" in i.filename.replace("\\", "/") for i in infos):
                strip = next(iter(tops)) + "/"
        for info in infos:
            total += int(info.file_size or 0)
            if total > MAX_EXTRACT_BYTES:
                raise ValueError(f"archive expands beyond {MAX_EXTRACT_BYTES // (1024*1024)} MB")
            count += 1
            if count > MAX_FILES:
                raise ValueError(f"archive contains more than {MAX_FILES} files")
            rel_name = info.filename.replace("\\", "/")
            if strip and rel_name.startswith(strip):
                rel_name = rel_name[len(strip):]
            if not rel_name:
                continue
            target = (dest / rel_name).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                raise ValueError(f"unsafe archive path rejected: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)
    return {"files": count, "bytes": total, "path": str(dest)}


def extract_zip(tid: str, zip_path: str | Path, archive_name: str = "") -> Dict[str, Any]:
    dest = _workdir(tid) / "projects" / _safe_archive_name(archive_name or Path(zip_path).stem)
    info = safe_extract_zip(zip_path, dest)
    proj = inspect_project(dest)
    t = load_task(tid)
    if t:
        _event(t, "archive_import", f"extracted {info['files']} files from {Path(zip_path).name}",
               path=str(dest.relative_to(_workdir(tid))).replace("\\", "/"),
               files=info["files"], bytes=info["bytes"])
        t["project"] = inspect_project(_workdir(tid))
        save_task(t)
    return {"task_id": tid, "extracted_to": str(dest.relative_to(_workdir(tid))).replace("\\", "/"),
            "files": info["files"], "bytes": info["bytes"], "project": proj}


def import_file(tid: str, filename: str, data: bytes) -> Dict[str, Any]:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"file too large (> {MAX_UPLOAD_BYTES // (1048576)} MB)")
    name = _safe_archive_name(filename)
    suffix = Path(name).suffix.lower()
    if suffix in _ARCHIVE_EXT:
        tmp = _workdir(tid) / ".exec" / f"upload_{uuid.uuid4().hex[:8]}{suffix}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        try:
            if suffix == ".zip":
                return extract_zip(tid, tmp, archive_name=Path(name).stem)
            # tar-like archives via tarfile
            import tarfile

            dest = _workdir(tid) / "projects" / Path(name).stem
            dest.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tmp) as tf:
                members = []
                for m in tf.getmembers():
                    if m.name.startswith("/") or ".." in Path(m.name).parts or m.issym() or m.islnk():
                        raise ValueError(f"unsafe archive member rejected: {m.name}")
                    members.append(m)
                if len(members) > MAX_FILES:
                    raise ValueError("archive contains too many files")
                tf.extractall(dest, members=members)
            t = load_task(tid)
            if t:
                _event(t, "archive_import", f"extracted {name}", files=len(members))
                t["project"] = inspect_project(_workdir(tid))
                save_task(t)
            return {"task_id": tid, "extracted_to": str(dest.relative_to(_workdir(tid))).replace("\\", "/"),
                    "files": len(members), "project": inspect_project(dest)}
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass

    target = _workdir(tid) / "uploads" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    t = load_task(tid)
    if t:
        _event(t, "file_upload", f"uploaded {name}", path=f"uploads/{name}", bytes=len(data))
        t["project"] = inspect_project(_workdir(tid))
        save_task(t)
    return {"task_id": tid, "path": f"uploads/{name}", "bytes": len(data),
            "project": inspect_project(_workdir(tid))}


# --------------------------------------------------------------------------- #
#  risk classification
# --------------------------------------------------------------------------- #
_DESTRUCTIVE = [
    r"\brm\s+-[^\n]*\s+/(\s|$)", r"\brm\s+-[^\n]*\s+\*",
    r"\bdel\s+/[fsq]", r"\bformat\s+[a-z]:", r"\bdiskpart\b",
    r"\bshutdown\b", r"\breboot\b", r"\breg\s+delete\b",
    r"\bmkfs\b", r"\bdd\s+if=", r":\(\)\s*\{", r"\bchmod\s+-R\s+777\s+/",
    r"remove-item[^\n]*-recurse[^\n]*-force[^\n]*(c:|/)",
    r"\bcipher\s+/w\b", r"\bvssadmin\s+delete",
]
_ELEVATED = [
    r"\bsudo\b", r"\brun\s+as\b", r"\bpsexec\b", r"-verb\s+runas",
    r"\b(pip|pip3)\s+install\b", r"\bnpm\s+install\s+-g\b",
    r"\bapt(-get)?\s+install\b", r"\bdnf\s+install\b", r"\byum\s+install\b",
    r"\bapk\s+add\b", r"\bpacman\s+-s\b", r"\bwinget\b", r"\bchoco\b",
]


def classify_command(command: str) -> Dict[str, Any]:
    cmd = str(command or "")
    for rx in _DESTRUCTIVE:
        if re.search(rx, cmd, re.IGNORECASE):
            return {"risk": "destructive", "requires_approval": True,
                    "reason": "irreversible / system-critical command shape"}
    for rx in _ELEVATED:
        if re.search(rx, cmd, re.IGNORECASE):
            return {"risk": "elevated", "requires_approval": True,
                    "reason": "privileged operation or package installation"}
    return {"risk": "safe", "requires_approval": False, "reason": ""}


# --------------------------------------------------------------------------- #
#  subprocess execution
# --------------------------------------------------------------------------- #
def _shell_argv(command: str, shell: str) -> List[str]:
    if os.name == "nt":
        if shell == "cmd":
            return ["cmd", "/c", command]
        return ["powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-Command", command]
    sh = shutil.which("bash") or "/bin/sh"
    return [sh, "-lc", command]


def _creation_flags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return 0


def _kill_tree(proc: Any) -> None:
    try:
        if proc.returncode is not None:
            return
    except Exception:
        pass
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, timeout=10)
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.terminate()
    except Exception:
        pass


async def _exec_argv(tid: str, argv: List[str], timeout: int, cwd: Optional[str] = None,
                     note: str = "") -> Dict[str, Any]:
    wd = str(cwd or _workdir(tid))
    started = _now()
    t = load_task(tid)
    if t:
        t["status"] = "running"
        t["started_at"] = t.get("started_at") or started
        _event(t, "exec_start", note or " ".join(argv)[:300], argv=argv[:6], cwd=wd)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=wd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=_creation_flags(),
        )
    except Exception as exc:
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                  "stdout": "", "stderr": "", "exit_code": None,
                  "duration_ms": int((_now() - started) * 1000)}
        if t:
            t["status"] = "failed"
            t["error"] = result["error"]
            t["finished_at"] = _now()
            _event(t, "exec_error", result["error"])
        return result

    with _PROC_LOCK:
        _PROCS[tid] = proc
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=max(1, int(timeout)))
        code = proc.returncode
        timed_out = False
    except asyncio.TimeoutError:
        _kill_tree(proc)
        try:
            stdout_b, stderr_b = await proc.communicate()
        except Exception:
            stdout_b, stderr_b = b"", b""
        code = None
        timed_out = True
    finally:
        with _PROC_LOCK:
            _PROCS.pop(tid, None)

    out = (stdout_b or b"").decode("utf-8", errors="replace")
    err = (stderr_b or b"").decode("utf-8", errors="replace")
    duration = int((_now() - started) * 1000)
    result = {
        "ok": (code == 0),
        "exit_code": code,
        "stdout": out[-MAX_OUTPUT:],
        "stderr": err[-MAX_OUTPUT:],
        "duration_ms": duration,
        "timeout": timed_out,
    }
    # reload: the task may have been cancelled while the process ran
    t2 = load_task(tid)
    if t2:
        t2["exit_code"] = code
        t2["result"] = {"stdout": out[-MAX_OUTPUT:], "stderr": err[-MAX_OUTPUT:],
                        "exit_code": code, "duration_ms": duration}
        if t2.get("status") == "cancelled":
            pass
        elif timed_out:
            t2["status"] = "failed"
            t2["error"] = f"timeout after {timeout}s"
        else:
            t2["status"] = "succeeded" if code == 0 else "failed"
            if code != 0:
                t2["error"] = (err.strip().splitlines() or ["non-zero exit"])[-1][:400]
        t2["finished_at"] = _now()
        _event(t2, "exec_finish", f"exit {code}", exit_code=code, duration_ms=duration,
               timed_out=timed_out)
    return result


async def run_command(tid: str, command: str, shell: str = "auto", timeout: int = DEFAULT_TIMEOUT,
                      cwd: Optional[str] = None, approved: bool = False,
                      background: bool = False) -> Dict[str, Any]:
    t = load_task(tid)
    if not t:
        raise KeyError(tid)
    if t.get("status") == "cancelled":
        return {"ok": False, "error": "task cancelled"}
    if shell == "auto":
        shell = "powershell" if os.name == "nt" else "bash"
    risk = classify_command(command)
    if risk["requires_approval"] and not (approved or t.get("approved")):
        _event(t, "approval_required", risk["reason"], command=command[:300], risk=risk["risk"])
        return {"ok": False, "requires_approval": True, "risk": risk["risk"],
                "reason": risk["reason"], "command": command[:300]}
    argv = _shell_argv(command, shell)
    if background:
        asyncio.create_task(_exec_argv(tid, argv, timeout, cwd, note=command[:200]))
        return {"ok": True, "background": True, "status": "running", "task_id": tid,
                "command": command[:300], "risk": risk["risk"]}
    res = await _exec_argv(tid, argv, timeout, cwd, note=command[:200])
    res.update({"task_id": tid, "command": command[:300], "risk": risk["risk"]})
    return res


async def run_python(tid: str, code: str, timeout: int = 60) -> Dict[str, Any]:
    t = load_task(tid)
    if not t:
        raise KeyError(tid)
    wd = _workdir(tid)
    (wd / ".exec").mkdir(parents=True, exist_ok=True)
    script = wd / ".exec" / f"run_{uuid.uuid4().hex[:8]}.py"
    script.write_text(code or "", encoding="utf-8")
    try:
        argv = [sys.executable, str(script)]
        res = await _exec_argv(tid, argv, timeout, str(wd), note=f"python {script.name}")
    finally:
        try:
            script.unlink()
        except Exception:
            pass
    res.update({"task_id": tid, "runner": "python"})
    return res


def cancel(tid: str) -> Dict[str, Any]:
    t = load_task(tid)
    if not t:
        raise KeyError(tid)
    with _PROC_LOCK:
        proc = _PROCS.get(tid)
    killed = False
    if proc is not None:
        _kill_tree(proc)
        killed = True
    t["status"] = "cancelled"
    t["finished_at"] = _now()
    _event(t, "cancelled", "cancelled by user", killed=killed)
    return {"ok": True, "task_id": tid, "killed": killed, "status": "cancelled"}


# --------------------------------------------------------------------------- #
#  artifacts / downloads
# --------------------------------------------------------------------------- #
def _safe_artifact_name(name: str) -> str:
    n = Path(str(name or "artifact.bin")).name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", n).strip("._") or "artifact.bin"


def make_archive(tid: str) -> Dict[str, Any]:
    t = load_task(tid)
    if not t:
        raise KeyError(tid)
    wd = _workdir(tid)
    out = ARCHIVES_DIR / f"{tid}.zip"
    tmp = ARCHIVES_DIR / f"{tid}.zip.tmp"
    count = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in wd.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(wd)
            if any(part in _SKIP_DIRS for part in rel.parts):
                continue
            zf.write(p, str(rel).replace("\\", "/"))
            count += 1
            if count > MAX_FILES:
                break
    os.replace(tmp, out)
    art = {"name": f"{tid}.zip", "path": str(out), "size": out.stat().st_size,
           "mime": "application/zip", "kind": "archive", "files": count, "created_at": _now(),
           "url": f"/api/exec/tasks/{tid}/archive"}
    t.setdefault("artifacts", []).append(art)
    _event(t, "artifact", f"archived {count} files", artifact=art["name"], bytes=art["size"])
    save_task(t)
    return art


def list_artifacts(tid: str) -> List[Dict[str, Any]]:
    t = load_task(tid)
    return list((t or {}).get("artifacts") or [])


def artifact_path(tid: str, name: str) -> Path:
    p = (ARCHIVES_DIR / _safe_artifact_name(name)).resolve()
    if ARCHIVES_DIR.resolve() not in p.parents and p.parent != ARCHIVES_DIR.resolve():
        raise ValueError("artifact path escapes artifact store")
    return p


def capabilities() -> Dict[str, Any]:
    fp = runtime_env.fingerprint()
    return {
        "ok": True,
        "fingerprint": fp,
        "summary": runtime_env.summary(),
        "environments": runtime_env.available_environments(),
        "limits": {
            "max_output": MAX_OUTPUT,
            "max_files": MAX_FILES,
            "max_extract_bytes": MAX_EXTRACT_BYTES,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
            "default_timeout": DEFAULT_TIMEOUT,
        },
        "security": {
            "path_traversal": "blocked",
            "archive_symlinks": "rejected",
            "destructive_commands": "require approval",
            "elevated_commands": "require approval",
        },
    }


# --------------------------------------------------------------------------- #
#  active-task context for agent tools
# --------------------------------------------------------------------------- #
def set_active_task(tid: Optional[str]) -> None:
    _ACTIVE_TASK.set(tid)


def get_active_task() -> Optional[str]:
    return _ACTIVE_TASK.get()


def active_workspace() -> Optional[str]:
    tid = _ACTIVE_TASK.get()
    if not tid:
        return None
    t = load_task(tid)
    return (t or {}).get("workdir")


async def run_in_active(command: str, timeout: int = DEFAULT_TIMEOUT, shell: str = "auto",
                        approved: bool = False) -> Dict[str, Any]:
    tid = _ACTIVE_TASK.get()
    if not tid:
        return {"ok": False, "error": "no active execution task"}
    return await run_command(tid, command, shell=shell, timeout=timeout, approved=approved)


def write_in_active(rel: str, content: str) -> Dict[str, Any]:
    tid = _ACTIVE_TASK.get()
    if not tid:
        return {"ok": False, "error": "no active execution task"}
    return write_file(tid, rel, content)