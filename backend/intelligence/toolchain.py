"""Dynamic toolchain discovery — never assumes a tool is installed."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
from typing import Any, Dict, List

# command -> (label, version args, supported inputs, operations)
EXTERNAL: Dict[str, Dict[str, Any]] = {
    "file": {"version": ["--version"], "inputs": ["*"], "ops": ["identify"]},
    "strings": {"version": ["--version"], "inputs": ["binary"], "ops": ["strings"]},
    "objdump": {"version": ["--version"], "inputs": ["elf", "pe", "object"], "ops": ["disassemble", "headers"]},
    "readelf": {"version": ["--version"], "inputs": ["elf"], "ops": ["headers", "sections", "symbols"]},
    "nm": {"version": ["--version"], "inputs": ["elf", "object"], "ops": ["symbols"]},
    "checksec": {"version": ["--version"], "inputs": ["elf", "pe"], "ops": ["hardening"]},
    "binwalk": {"version": ["--version"], "inputs": ["firmware", "archive"], "ops": ["extract", "identify"]},
    "r2": {"version": ["-v"], "inputs": ["elf", "pe", "dex"], "ops": ["disassemble", "analyze"]},
    "radare2": {"version": ["-v"], "inputs": ["elf", "pe", "dex"], "ops": ["disassemble", "analyze"]},
    "rizin": {"version": ["-v"], "inputs": ["elf", "pe", "dex"], "ops": ["disassemble", "analyze"]},
    "ghidra": {"version": ["--version"], "inputs": ["elf", "pe", "dex"], "ops": ["decompile"]},
    "ida": {"version": ["--version"], "inputs": ["elf", "pe"], "ops": ["decompile"]},
    "retdec-decompiler": {"version": ["--version"], "inputs": ["elf", "pe"], "ops": ["decompile"]},
    "ilspycmd": {"version": ["--version"], "inputs": ["dll", "exe"], "ops": ["decompile"]},
    "jadx": {"version": ["--version"], "inputs": ["apk", "dex", "jar"], "ops": ["decompile"]},
    "apktool": {"version": ["--version"], "inputs": ["apk"], "ops": ["extract", "decode"]},
    "aapt": {"version": ["version"], "inputs": ["apk"], "ops": ["manifest"]},
    "aapt2": {"version": ["version"], "inputs": ["apk"], "ops": ["manifest"]},
    "javap": {"version": ["-version"], "inputs": ["class", "jar"], "ops": ["disassemble"]},
    "cfr": {"version": ["--version"], "inputs": ["jar", "class"], "ops": ["decompile"]},
    "git": {"version": ["--version"], "inputs": ["project"], "ops": ["diff", "status"]},
    "python": {"version": ["--version"], "inputs": ["project"], "ops": ["test", "build"]},
    "node": {"version": ["--version"], "inputs": ["project"], "ops": ["test", "build"]},
    "npm": {"version": ["--version"], "inputs": ["project"], "ops": ["test", "build"]},
}

MODULES: Dict[str, Dict[str, Any]] = {
    "pefile": {"inputs": ["pe"], "ops": ["identify", "imports", "exports", "sections", "resources"]},
    "elftools": {"inputs": ["elf"], "ops": ["identify", "sections", "symbols", "imports"]},
    "capstone": {"inputs": ["elf", "pe", "raw"], "ops": ["disassemble"]},
    "lief": {"inputs": ["elf", "pe", "dex", "macho"], "ops": ["identify", "parse"]},
    "androguard": {"inputs": ["apk", "dex"], "ops": ["manifest", "decompile"]},
}


def _version(cmd: str, args: List[str]) -> str:
    try:
        out = subprocess.run([cmd, *args], capture_output=True, text=True, timeout=6)
        text = (out.stdout or out.stderr or "").strip().splitlines()
        return text[0][:160] if text else "unknown"
    except Exception:
        return "unknown"


def discover() -> Dict[str, Any]:
    tools: List[Dict[str, Any]] = []
    for name, meta in EXTERNAL.items():
        path = shutil.which(name)
        tools.append({
            "name": name,
            "kind": "executable",
            "available": bool(path),
            "path": path or "",
            "version": _version(name, meta["version"]) if path else "",
            "inputs": meta["inputs"],
            "operations": meta["ops"],
            "environment": "local",
            "health": "ok" if path else "missing",
        })
    for name, meta in MODULES.items():
        spec = importlib.util.find_spec(name)
        module = None
        if spec:
            try:
                module = importlib.import_module(name)
            except Exception:
                module = None
        tools.append({
            "name": name,
            "kind": "python-module",
            "available": module is not None,
            "path": str(getattr(module, "__file__", "") or ""),
            "version": str(getattr(module, "__version__", "") or ""),
            "inputs": meta["inputs"],
            "operations": meta["ops"],
            "environment": "local-python",
            "health": "ok" if module else "missing",
        })
    return {
        "environment": "windows-local" if __import__("sys").platform == "win32" else "posix-local",
        "tools": tools,
        "available": [t["name"] for t in tools if t["available"]],
        "missing": [t["name"] for t in tools if not t["available"]],
    }


def pick(artifact_format: str, operation: str) -> List[str]:
    report = discover()
    out = []
    for tool in report["tools"]:
        if tool["available"] and artifact_format in tool["inputs"] and operation in tool["operations"]:
            out.append(tool["name"])
    return out
