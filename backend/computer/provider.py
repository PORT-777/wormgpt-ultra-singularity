"""Provider-independent sandbox interface.

Every provider adapter implements this contract. Production adapters must use
real isolated infrastructure (Daytona/Firecracker-equivalent); the Docker
adapter is explicitly development-only and must never be represented as
hardware-isolated.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Resources:
    cpu: int = 1
    memory_gb: int = 2
    disk_gb: int = 10
    timeout_seconds: int = 300
    network: bool = True


@dataclass
class ExecResult:
    ok: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    session_id: str = ""
    error: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok, "exit_code": self.exit_code,
            "stdout": self.stdout[-20000:], "stderr": self.stderr[-20000:],
            "duration_ms": self.duration_ms, "session_id": self.session_id,
            "error": self.error,
        }


@dataclass
class FileInfo:
    path: str
    is_dir: bool = False
    size: int = 0
    modified: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "is_dir": self.is_dir, "size": self.size, "modified": self.modified}


@dataclass
class ProcessInfo:
    pid: str
    command: str
    status: str = "running"
    port: Optional[int] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"pid": self.pid, "command": self.command, "status": self.status, "port": self.port}


@dataclass
class ComputerInfo:
    id: str
    provider: str
    mode: str
    status: str
    os: str = ""
    resources: Resources = field(default_factory=Resources)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "provider": self.provider, "mode": self.mode,
            "status": self.status, "os": self.os,
            "resources": self.resources.__dict__, "metadata": self.metadata,
        }


class SandboxProvider(ABC):
    """All operations are real; no provider may fabricate output."""

    name = "abstract"

    @abstractmethod
    def configured(self) -> bool:
        ...

    @abstractmethod
    def create(self, *, computer_id: str, mode: str, resources: Resources,
               image: str = "") -> ComputerInfo:
        ...

    @abstractmethod
    def start(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        ...

    @abstractmethod
    def stop(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        ...

    @abstractmethod
    def restart(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        ...

    @abstractmethod
    def delete(self, computer_id: str, provider_ref: str) -> bool:
        ...

    @abstractmethod
    def execute(self, computer_id: str, provider_ref: str, command: str, *,
                cwd: str = "", timeout: int = 60, env: Optional[Dict[str, str]] = None,
                session_id: str = "") -> ExecResult:
        ...

    @abstractmethod
    def list_files(self, computer_id: str, provider_ref: str, path: str) -> List[FileInfo]:
        ...

    @abstractmethod
    def read_file(self, computer_id: str, provider_ref: str, path: str) -> str:
        ...

    @abstractmethod
    def write_file(self, computer_id: str, provider_ref: str, path: str, content: str) -> bool:
        ...

    @abstractmethod
    def delete_file(self, computer_id: str, provider_ref: str, path: str) -> bool:
        ...

    @abstractmethod
    def list_processes(self, computer_id: str, provider_ref: str) -> List[ProcessInfo]:
        ...

    @abstractmethod
    def stop_process(self, computer_id: str, provider_ref: str, pid: str) -> bool:
        ...

    @abstractmethod
    def resources(self, computer_id: str, provider_ref: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def screenshot(self, computer_id: str, provider_ref: str) -> Optional[str]:
        """Return a provider-hosted screenshot path/URL, or None if unsupported."""
        ...
