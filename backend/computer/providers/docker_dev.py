"""Docker-based DEVELOPMENT adapter.

This adapter uses ordinary shared-kernel containers. It is for local development
and tests only and must never be represented as hardware-isolated. Production
must use Daytona/Firecracker-equivalent isolation.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from ..provider import (
    ComputerInfo, ExecResult, FileInfo, ProcessInfo, Resources, SandboxProvider,
)

_IMAGE = os.getenv("COMPUTER_DEV_IMAGE", "ubuntu:24.04")


class DockerDevProvider(SandboxProvider):
    name = "docker-dev"

    def configured(self) -> bool:
        return shutil.which("docker") is not None

    def _docker(self, args: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
        if not self.configured():
            raise RuntimeError("docker CLI is not installed — development adapter unavailable")
        return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)

    def create(self, *, computer_id: str, mode: str, resources: Resources,
               image: str = "") -> ComputerInfo:
        name = f"port777-{computer_id}-{mode}"
        cp = self._docker([
            "run", "-d", "--name", name,
            "--cpus", str(resources.cpu),
            "--memory", f"{resources.memory_gb}g",
            "--network", "bridge" if resources.network else "none",
            "-w", "/workspace",
            image or _IMAGE,
            "sleep", "infinity",
        ])
        if cp.returncode != 0:
            raise RuntimeError(f"docker run failed: {cp.stderr.strip()[:500]}")
        self.execute(computer_id, name, "apt-get update -qq && DEBIAN_FRONTEND=noninteractive "
                     "apt-get install -y -qq python3 python3-pip nodejs npm git curl wget jq unzip zip "
                     "build-essential gcc g++ make cmake openssl sqlite3 ca-certificates", timeout=600)
        return ComputerInfo(computer_id, self.name, mode, "running", "Ubuntu 24.04 (Docker dev)",
                            resources, {"provider_ref": name, "isolation": "shared-kernel-container",
                                        "dev_only": True})

    def start(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        cp = self._docker(["start", provider_ref]); cp.check_returncode()
        return ComputerInfo(computer_id, self.name, "persistent", "running")

    def stop(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        cp = self._docker(["stop", provider_ref]); cp.check_returncode()
        return ComputerInfo(computer_id, self.name, "persistent", "stopped")

    def restart(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        cp = self._docker(["restart", provider_ref]); cp.check_returncode()
        return ComputerInfo(computer_id, self.name, "persistent", "running")

    def delete(self, computer_id: str, provider_ref: str) -> bool:
        cp = self._docker(["rm", "-f", provider_ref])
        return cp.returncode == 0

    def execute(self, computer_id: str, provider_ref: str, command: str, *,
                cwd: str = "", timeout: int = 60, env: Optional[Dict[str, str]] = None,
                session_id: str = "") -> ExecResult:
        started = time.time()
        args = ["exec", "-w", cwd or "/workspace"]
        for k, v in (env or {}).items():
            args += ["-e", f"{k}={v}"]
        args += [provider_ref, "bash", "-lc", command]
        try:
            cp = self._docker(args, timeout=timeout)
            return ExecResult(cp.returncode == 0, cp.returncode, cp.stdout, cp.stderr,
                              int((time.time() - started) * 1000))
        except Exception as exc:
            return ExecResult(False, -1, "", "", int((time.time() - started) * 1000),
                              "", f"{type(exc).__name__}: {exc}")

    def list_files(self, computer_id: str, provider_ref: str, path: str) -> List[FileInfo]:
        r = self.execute(computer_id, provider_ref,
                         f"ls -la --time-style=+%s {shlex.quote(path or '/workspace')}")
        out = []
        for line in r.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 7:
                out.append(FileInfo(parts[-1], parts[0].startswith("d"),
                                    int(parts[4]) if parts[4].isdigit() else 0,
                                    float(parts[5]) if parts[5].replace('.', '', 1).isdigit() else 0))
        return out

    def read_file(self, computer_id: str, provider_ref: str, path: str) -> str:
        return self.execute(computer_id, provider_ref, f"cat {shlex.quote(path)}").stdout

    def write_file(self, computer_id: str, provider_ref: str, path: str, content: str) -> bool:
        cp = subprocess.run(["docker", "exec", "-i", provider_ref, "tee", path],
                            input=content.encode(), capture_output=True, timeout=120)
        return cp.returncode == 0

    def delete_file(self, computer_id: str, provider_ref: str, path: str) -> bool:
        return self.execute(computer_id, provider_ref, f"rm -rf {shlex.quote(path)}").ok

    def list_processes(self, computer_id: str, provider_ref: str) -> List[ProcessInfo]:
        r = self.execute(computer_id, provider_ref, "ps -eo pid=,args= --sort=-pid | head -200")
        out = []
        for line in r.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                out.append(ProcessInfo(parts[0], parts[1]))
        return out

    def stop_process(self, computer_id: str, provider_ref: str, pid: str) -> bool:
        return self.execute(computer_id, provider_ref, f"kill -9 {shlex.quote(pid)}").ok

    def resources(self, computer_id: str, provider_ref: str) -> Dict[str, Any]:
        cp = self._docker(["stats", "--no-stream", "--format",
                           "{{.CPUPerc}}|{{.MemUsage}}|{{.NetIO}}", provider_ref])
        return {"source": "docker stats (real)", "raw": cp.stdout.strip()}

    def screenshot(self, computer_id: str, provider_ref: str) -> Optional[str]:
        return None  # dev adapter has no desktop; use Daytona computer_use in production
