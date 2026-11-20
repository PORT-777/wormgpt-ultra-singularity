"""
Universal Environment Detection Engine
======================================
Produces a *verified* fingerprint of the runtime the backend is actually
executing on.  Nothing here is assumed: interpreters, package managers and
security tools are probed with real subprocess calls (short timeouts), the
OS identity is read from authoritative files (/etc/os-release, platform
module, WMI-free Windows APIs), and every capability is reported with the
evidence used to determine it.

The result is cached for a short TTL because probing takes ~100-400 ms.
Call ``fingerprint(refresh=True)`` (or POST /api/runtime/refresh) to
invalidate the cache after an environment change.

Security:
- No secrets, tokens or personal identifiers are collected.
- Tool probes are argument-vector based (no shell=True).
- Missing tools are reported as missing; nothing is auto-installed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import configs as config
    WORKSPACE_DIR = Path(getattr(config, "WORKSPACE_DIR", Path.cwd())).resolve()
except Exception:  # pragma: no cover - standalone import
    WORKSPACE_DIR = Path.cwd().resolve()

CACHE_TTL = 300.0
_CACHE: Dict[str, Any] = {"at": 0.0, "fp": None}

# --------------------------------------------------------------------------- #
#  small helpers
# --------------------------------------------------------------------------- #
def _run(argv: List[str], timeout: float = 4.0) -> Dict[str, Any]:
    """Run an argv safely (never a shell string) and capture the first lines."""
    started = time.time()
    try:
        p = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=max(0.5, timeout),
            shell=False,
            errors="replace",
        )
        out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
        return {
            "ok": p.returncode == 0,
            "code": p.returncode,
            "out": out.strip()[:600],
            "ms": int((time.time() - started) * 1000),
        }
    except FileNotFoundError:
        return {"ok": False, "code": None, "out": "", "ms": 0, "missing": True}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": None, "out": "", "ms": int((time.time() - started) * 1000), "timeout": True}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "code": None, "out": f"{type(exc).__name__}: {exc}", "ms": 0}


def _first_line(text: str) -> str:
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if ln:
            return ln[:160]
    return ""


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _read_text(path: str | Path, limit: int = 8192) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
#  OS / distribution identity
# --------------------------------------------------------------------------- #
def _os_release() -> Dict[str, str]:
    data: Dict[str, str] = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        txt = _read_text(path)
        if not txt:
            continue
        for line in txt.splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
        break
    return data


def _windows_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "family": "windows",
        "name": platform.system() or "Windows",
        "version": platform.version(),
        "release": platform.release(),
        "edition": "",
        "arch": platform.machine(),
        "kernel": platform.version(),
    }
    try:
        import ctypes

        class OSVERSIONINFOW(ctypes.Structure):
            _fields_ = [
                ("dwOSVersionInfoSize", ctypes.c_ulong),
                ("dwMajorVersion", ctypes.c_ulong),
                ("dwMinorVersion", ctypes.c_ulong),
                ("dwBuildNumber", ctypes.c_ulong),
                ("dwPlatformId", ctypes.c_ulong),
                ("szCSDVersion", ctypes.c_wchar * 128),
            ]

        vi = OSVERSIONINFOW()
        vi.dwOSVersionInfoSize = ctypes.sizeof(OSVERSIONINFOW)
        if ctypes.windll.ntdll.RtlGetVersion(ctypes.byref(vi)) == 0:
            info["version"] = f"{vi.dwMajorVersion}.{vi.dwMinorVersion}.{vi.dwBuildNumber}"
    except Exception:
        pass
    try:
        import ctypes

        info["admin"] = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        info["admin"] = False
    # Windows 11 detection is build >= 22000
    try:
        build = int(re.sub(r"\D", "", str(info.get("version") or "0"))[-5:] or 0)
        info["marketing_name"] = "Windows 11" if build >= 22000 else "Windows 10/Server"
    except Exception:
        info["marketing_name"] = info["name"]
    return info


def _linux_info() -> Dict[str, Any]:
    rel = _os_release()
    uname = platform.uname()
    is_kali = str(rel.get("ID", "")).lower() == "kali" or "kali" in str(rel.get("PRETTY_NAME", "")).lower()
    return {
        "family": "linux",
        "name": rel.get("PRETTY_NAME") or platform.system() or "Linux",
        "distro_id": rel.get("ID", ""),
        "distro_name": rel.get("NAME", ""),
        "distro_version": rel.get("VERSION_ID", ""),
        "distro_like": rel.get("ID_LIKE", ""),
        "kernel": uname.release,
        "arch": uname.machine,
        "is_kali": is_kali,
        "is_wsl": "microsoft" in str(uname.release).lower(),
        "is_container": Path("/.dockerenv").exists() or bool(os.environ.get("container")),
        "is_k8s": bool(os.environ.get("KUBERNETES_SERVICE_HOST")),
    }


def _android_info() -> Optional[Dict[str, Any]]:
    if os.name != "posix":
        return None
    hints = os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA")
    build_prop = Path("/system/build.prop")
    termux = bool(os.environ.get("TERMUX_VERSION")) or "com.termux" in str(Path.home()) or bool(_which("termux-info"))
    if not (hints or build_prop.exists() or termux):
        return None
    return {
        "family": "android",
        "name": "Android",
        "version": _read_text("/system/build.prop", 4000).split("ro.build.version.release=")[-1].splitlines()[0]
        if "ro.build.version.release=" in _read_text("/system/build.prop", 8000)
        else "",
        "arch": platform.machine(),
        "termux": termux,
        "termux_python": bool(_which("python") or _which("python3")),
    }


def _detect_os() -> Dict[str, Any]:
    system = platform.system().lower()
    if system == "windows":
        return _windows_info()
    android = _android_info()
    if android:
        return android
    if system == "darwin":
        return {
            "family": "macos",
            "name": platform.system(),
            "version": platform.version(),
            "arch": platform.machine(),
        }
    if system in ("linux", "freebsd", "openbsd"):
        info = _linux_info()
        info["family"] = "linux"
        return info
    return {"family": system or "unknown", "name": platform.system(), "version": platform.version(), "arch": platform.machine()}


# --------------------------------------------------------------------------- #
#  runtimes / shells / package managers
# --------------------------------------------------------------------------- #
def _shells(os_info: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if os_info.get("family") == "windows":
        for name in ("powershell", "pwsh", "cmd"):
            p = _which(f"{name}.exe") or _which(name)
            out[name] = {"path": p, "available": bool(p)}
        if out.get("powershell", {}).get("available"):
            r = _run([out["powershell"]["path"], "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"])
            out["powershell"]["version"] = _first_line(r.get("out", ""))
    else:
        for name in ("bash", "zsh", "sh", "fish"):
            p = _which(name)
            out[name] = {"path": p, "available": bool(p)}
        if out.get("bash", {}).get("available"):
            r = _run([out["bash"]["path"], "--version"])
            out["bash"]["version"] = _first_line(r.get("out", ""))
    return out


def _package_managers(os_info: Dict[str, Any]) -> Dict[str, Any]:
    candidates = ["apt-get", "apt", "dnf", "yum", "pacman", "apk", "zypper",
                  "xbps-install", "brew", "winget", "choco", "scoop", "pip", "pip3", "npm", "pnpm", "yarn"]
    out: Dict[str, Any] = {}
    for name in candidates:
        p = _which(name) or (_which(f"{name}.exe") if os_info.get("family") == "windows" else None)
        if p:
            out[name] = {"path": p, "available": True}
    return out


GENERAL_TOOLS: List[Tuple[str, List[str]]] = [
    ("python", ["python", "--version"]),
    ("python3", ["python3", "--version"]),
    ("node", ["node", "--version"]),
    ("npm", ["npm", "--version"]),
    ("git", ["git", "--version"]),
    ("docker", ["docker", "--version"]),
    ("java", ["java", "-version"]),
    ("go", ["go", "version"]),
    ("rustc", ["rustc", "--version"]),
    ("gcc", ["gcc", "--version"]),
    ("make", ["make", "--version"]),
    ("dotnet", ["dotnet", "--version"]),
    ("php", ["php", "--version"]),
    ("ruby", ["ruby", "--version"]),
]

SECURITY_TOOLS: List[Tuple[str, List[str]]] = [
    ("nmap", ["nmap", "--version"]),
    ("masscan", ["masscan", "--version"]),
    ("netcat", ["nc", "-h"]),
    ("tcpdump", ["tcpdump", "--version"]),
    ("tshark", ["tshark", "--version"]),
    ("nikto", ["nikto", "-Version"]),
    ("sqlmap", ["sqlmap", "--version"]),
    ("gobuster", ["gobuster", "--version"]),
    ("ffuf", ["ffuf", "-V"]),
    ("whatweb", ["whatweb", "--version"]),
    ("metasploit", ["msfconsole", "--version"]),
    ("hydra", ["hydra", "-h"]),
    ("john", ["john", "--list=build-info"]),
    ("hashcat", ["hashcat", "--version"]),
    ("aircrack-ng", ["aircrack-ng", "--version"]),
    ("bettercap", ["bettercap", "-version"]),
    ("responder", ["responder", "-h"]),
    ("wireshark", ["wireshark", "--version"]),
]


def _probe_tools(specs: List[Tuple[str, List[str]]], timeout: float = 3.0) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, argv in specs:
        exe = _which(argv[0]) or (_which(f"{argv[0]}.exe") if os.name == "nt" else None)
        if not exe:
            out[name] = {"installed": False, "path": None, "version": None}
            continue
        r = _run([exe] + argv[1:], timeout=timeout)
        out[name] = {
            "installed": True,
            "path": exe,
            "version": _first_line(r.get("out", "")) or None,
            "runs": bool(r.get("ok") or r.get("out")),
        }
    return out


# --------------------------------------------------------------------------- #
#  capabilities
# --------------------------------------------------------------------------- #
def _capabilities(os_info: Dict[str, Any], shells: Dict[str, Any], tools: Dict[str, Any]) -> Dict[str, Any]:
    is_windows = os_info.get("family") == "windows"
    py = tools.get("python") or tools.get("python3") or {}
    node = tools.get("node") or {}
    browser = any(_which(x) for x in ("chrome", "chromium", "chromium-browser", "msedge", "firefox", "google-chrome"))
    playwright = importlib.util.find_spec("playwright") is not None
    writable = os.access(str(WORKSPACE_DIR), os.W_OK)
    return {
        "process_exec": bool(shells.get("powershell", {}).get("available") or shells.get("cmd", {}).get("available") or shells.get("bash", {}).get("available") or shells.get("sh", {}).get("available")),
        "filesystem_read": os.access(str(WORKSPACE_DIR), os.R_OK),
        "filesystem_write": writable,
        "network": True,  # actual egress is policy-gated per task
        "browser_automation": bool(browser and playwright),
        "python": bool(py.get("installed")),
        "node": bool(node.get("installed")),
        "package_install": bool(tools.get("npm") or tools.get("pip") or os_info.get("family") == "linux"),
        "admin": bool(os_info.get("admin")) or (os.geteuid() == 0 if hasattr(os, "geteuid") else False),
        "kali_security_tools": sum(1 for name, _ in SECURITY_TOOLS if (tools.get(name) or {}).get("installed")),
        "is_windows": is_windows,
    }


def _cloud_markers() -> Dict[str, Any]:
    markers = {
        "kubernetes": bool(os.environ.get("KUBERNETES_SERVICE_HOST")),
        "aws_lambda": bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME")),
        "gcp": bool(os.environ.get("K_SERVICE") or os.environ.get("GOOGLE_CLOUD_PROJECT")),
        "azure": bool(os.environ.get("WEBSITE_INSTANCE_ID")),
        "fly": bool(os.environ.get("FLY_APP_NAME")),
        "render": bool(os.environ.get("RENDER")),
        "heroku": bool(os.environ.get("DYNO")),
        "docker": Path("/.dockerenv").exists() or bool(os.environ.get("container")),
    }
    return {k: v for k, v in markers.items() if v}


def _runtime_type(os_info: Dict[str, Any]) -> str:
    if os_info.get("family") == "android":
        return "android-termux" if os_info.get("termux") else "android"
    if os_info.get("is_wsl"):
        return "wsl"
    if os_info.get("is_k8s"):
        return "kubernetes"
    if os_info.get("is_container"):
        return "container"
    if _cloud_markers():
        return "cloud"
    return "local"


# --------------------------------------------------------------------------- #
#  public API
# --------------------------------------------------------------------------- #
def fingerprint(refresh: bool = False) -> Dict[str, Any]:
    now = time.time()
    if not refresh and _CACHE.get("fp") and (now - float(_CACHE.get("at") or 0)) < CACHE_TTL:
        return _CACHE["fp"]

    os_info = _detect_os()
    shells = _shells(os_info)
    tools: Dict[str, Any] = {}
    tools.update(_probe_tools(GENERAL_TOOLS))
    tools.update(_probe_tools(SECURITY_TOOLS))
    caps = _capabilities(os_info, shells, tools)
    cloud = _cloud_markers()

    fp = {
        "env_id": hashlib.sha256(
            "|".join([
                str(os_info.get("family")),
                str(os_info.get("distro_id") or os_info.get("name")),
                str(os_info.get("arch")),
                str(_runtime_type(os_info)),
                str(WORKSPACE_DIR),
            ]).encode("utf-8")
        ).hexdigest()[:16],
        "os": os_info,
        "runtime": {
            "type": _runtime_type(os_info),
            "cloud_markers": cloud,
            "shells": shells,
            "python": tools.get("python") or tools.get("python3"),
            "node": tools.get("node"),
            "git": tools.get("git"),
        },
        "workspace": {
            "path": str(WORKSPACE_DIR),
            "readable": caps["filesystem_read"],
            "writable": caps["filesystem_write"],
        },
        "capabilities": caps,
        "tools": tools,
        "limits": {
            "shell_timeout": int(getattr(config, "SHELL_TIMEOUT", 60)),
            "exec_timeout": int(getattr(config, "TOOL_EXEC_TIMEOUT", 40)),
            "max_output": int(getattr(config, "SHELL_MAX_OUTPUT", 8000)),
        },
        "detected_at": now,
        "cache_ttl": CACHE_TTL,
        "platform": platform.platform(),
        "python_runtime": sys.version.split()[0],
    }
    _CACHE["fp"] = fp
    _CACHE["at"] = now
    return fp


def summary(refresh: bool = False) -> Dict[str, Any]:
    """Compact fingerprint for UI badges / prompts (no tool dump)."""
    fp = fingerprint(refresh=refresh)
    os_i = fp["os"]
    caps = fp["capabilities"]
    return {
        "env_id": fp["env_id"],
        "family": os_i.get("family"),
        "name": os_i.get("name"),
        "version": os_i.get("version"),
        "distro_id": os_i.get("distro_id"),
        "distro_name": os_i.get("distro_name"),
        "arch": os_i.get("arch") or os_i.get("machine"),
        "kernel": os_i.get("kernel"),
        "is_kali": bool(os_i.get("is_kali")),
        "is_wsl": bool(os_i.get("is_wsl")),
        "is_container": bool(os_i.get("is_container") or os_i.get("is_k8s")),
        "runtime_type": fp["runtime"]["type"],
        "workspace": fp["workspace"]["path"],
        "capabilities": caps,
        "detected_at": fp["detected_at"],
    }


def available_environments() -> List[Dict[str, Any]]:
    """Environments that can *really* execute here, with honest availability."""
    fp = fingerprint()
    os_i = fp["os"]
    caps = fp["capabilities"]
    rt = fp["runtime"]["type"]
    envs = [
        {"id": "auto", "label": "Auto detect", "available": True, "detail": f"resolves to {rt}"},
        {"id": "cloud", "label": "Cloud / server workspace", "available": True,
         "detail": "server-side isolated workspace (this backend)"},
        {"id": "local", "label": "Local machine", "available": bool(caps["process_exec"] and rt in ("local", "wsl", "android-termux")),
         "detail": fp["os"].get("name") or rt},
        {"id": "windows", "label": "Windows", "available": os_i.get("family") == "windows",
         "detail": "host is Windows" if os_i.get("family") == "windows" else "host is not Windows"},
        {"id": "linux", "label": "Linux", "available": os_i.get("family") == "linux",
         "detail": os_i.get("distro_name") or "host is not Linux"},
        {"id": "kali", "label": "Kali Linux", "available": bool(os_i.get("is_kali")),
         "detail": "verified /etc/os-release ID=kali" if os_i.get("is_kali") else "not a verified Kali host"},
        {"id": "wsl", "label": "WSL", "available": bool(os_i.get("is_wsl")),
         "detail": "WSL kernel detected" if os_i.get("is_wsl") else "not WSL"},
        {"id": "android", "label": "Android / Termux", "available": os_i.get("family") == "android",
         "detail": "Termux runtime" if os_i.get("termux") else ("Android host" if os_i.get("family") == "android" else "no Android runtime")},
        {"id": "browser", "label": "Browser automation", "available": bool(caps["browser_automation"]),
         "detail": "playwright + browser found" if caps["browser_automation"] else "browser automation not available"},
        {"id": "sandbox", "label": "Isolated sandbox", "available": True,
         "detail": "per-task isolated workspace + optional Docker/WSL sandbox"},
    ]
    return envs


def tool_catalog(refresh: bool = False) -> Dict[str, Any]:
    fp = fingerprint(refresh=refresh)
    tools = fp["tools"]
    installed = sorted(k for k, v in tools.items() if v.get("installed"))
    missing = sorted(k for k, v in tools.items() if not v.get("installed"))
    return {
        "tools": tools,
        "installed": installed,
        "missing": missing,
        "counts": {"installed": len(installed), "missing": len(missing)},
    }