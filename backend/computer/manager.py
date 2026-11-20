"""AI Computer lifecycle manager.

Selects a provider, enforces per-user ownership and limits, records audit logs,
and exposes one API for agent tools and HTTP routes.
"""
from __future__ import annotations

import json
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import configs as config

from . import store
from .provider import ComputerInfo, ExecResult, FileInfo, ProcessInfo, Resources, SandboxProvider
from .providers.daytona import DaytonaProvider
from .providers.docker_dev import DockerDevProvider

_PROVIDERS: Dict[str, SandboxProvider] = {
    "daytona": DaytonaProvider(),
    "docker-dev": DockerDevProvider(),
}


def provider_names() -> List[str]:
    return list(_PROVIDERS)


def provider_status() -> List[Dict[str, Any]]:
    out = []
    for name, p in _PROVIDERS.items():
        out.append({"name": name, "configured": p.configured(),
                    "production_isolation": name == "daytona",
                    "notes": "microVM isolation" if name == "daytona" else "development only, shared kernel"})
    return out


class ComputerManager:
    def __init__(self) -> None:
        store.init_tables()

    def _provider(self, name: Optional[str] = None) -> SandboxProvider:
        chosen = (name or getattr(config, "COMPUTER_PROVIDER", "daytona")).strip().lower()
        p = _PROVIDERS.get(chosen)
        if p is None:
            raise RuntimeError(f"unknown computer provider: {chosen}")
        if not p.configured():
            if chosen == "daytona":
                raise RuntimeError(
                    "Daytona is not configured. Set DAYTONA_API_KEY (and optionally "
                    "DAYTONA_API_URL, DAYTONA_TARGET) in backend/.env, then install "
                    "the SDK with: pip install \"daytona<1\""
                )
            raise RuntimeError(f"provider {chosen} is not configured on this host")
        return p

    def _resources(self, payload: Optional[Dict[str, Any]] = None) -> Resources:
        payload = payload or {}
        return Resources(
            cpu=int(payload.get("cpu") or getattr(config, "COMPUTER_CPU", 1)),
            memory_gb=int(payload.get("memory_gb") or getattr(config, "COMPUTER_MEMORY_GB", 2)),
            disk_gb=int(payload.get("disk_gb") or getattr(config, "COMPUTER_DISK_GB", 10)),
            timeout_seconds=int(payload.get("timeout_seconds") or getattr(config, "COMPUTER_TIMEOUT", 300)),
            network=bool(payload.get("network", True)),
        )

    def _check_limit(self, user_id: str) -> None:
        limit = int(getattr(config, "COMPUTER_MAX_PER_USER", 5))
        active = [c for c in store.list_computers(user_id, 500) if c.get("status") == "running"]
        if len(active) >= limit:
            raise RuntimeError(f"computer limit reached for user ({len(active)}/{limit})")

    def create(self, *, user_id: str, mode: str = "temporary", name: str = "",
               resources: Optional[Dict[str, Any]] = None,
               provider: Optional[str] = None) -> Dict[str, Any]:
        if mode not in ("temporary", "persistent"):
            raise ValueError("mode must be temporary or persistent")
        self._check_limit(user_id)
        p = self._provider(provider)
        cid = f"cmp-{uuid.uuid4().hex[:12]}"
        res = self._resources(resources)
        info = p.create(computer_id=cid, mode=mode, resources=res,
                        image=getattr(config, "COMPUTER_IMAGE", ""))
        row = {
            "id": cid, "user_id": user_id, "name": name or f"{mode}-{cid[:8]}",
            "mode": mode, "provider": info.provider, "provider_ref": info.metadata["provider_ref"],
            "status": info.status, "os": info.os, "resources": res.__dict__,
            "metadata": info.metadata, "created": time.time(),
        }
        store.save_computer(row)
        store.add_log("system", cid, user_id, "info", f"created {mode} computer via {info.provider}")
        if mode == "persistent":
            self.execute(cid, user_id, "mkdir -p /home/daytona/projects")
        return self.get(cid, user_id)

    def get(self, computer_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        row = store.get_computer(computer_id, user_id)
        if not row:
            raise KeyError(f"computer not found: {computer_id}")
        return row

    def list(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return store.list_computers(user_id)

    def _with_provider(self, computer_id: str, user_id: Optional[str]):
        row = self.get(computer_id, user_id)
        return row, self._provider(row["provider"])

    def start(self, computer_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        row, p = self._with_provider(computer_id, user_id)
        info = p.start(computer_id, row["provider_ref"])
        row["status"] = info.status; store.save_computer(row)
        return self.get(computer_id, user_id or row["user_id"])

    def stop(self, computer_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        row, p = self._with_provider(computer_id, user_id)
        info = p.stop(computer_id, row["provider_ref"])
        row["status"] = info.status; store.save_computer(row)
        return self.get(computer_id, user_id or row["user_id"])

    def restart(self, computer_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        row, p = self._with_provider(computer_id, user_id)
        info = p.restart(computer_id, row["provider_ref"])
        row["status"] = info.status; store.save_computer(row)
        return self.get(computer_id, user_id or row["user_id"])

    def delete(self, computer_id: str, user_id: Optional[str] = None) -> bool:
        row, p = self._with_provider(computer_id, user_id)
        ok = p.delete(computer_id, row["provider_ref"])
        if ok:
            store.delete_computer(computer_id, user_id or row["user_id"])
        return ok

    def execute(self, computer_id: str, user_id: Optional[str], command: str, *,
                cwd: str = "", timeout: int = 60, env: Optional[Dict[str, str]] = None,
                session_id: str = "", job_id: str = "") -> Dict[str, Any]:
        row, p = self._with_provider(computer_id, user_id)
        r: ExecResult = p.execute(computer_id, row["provider_ref"], command, cwd=cwd,
                                  timeout=timeout, env=env, session_id=session_id)
        if job_id:
            store.add_log(job_id, computer_id, row["user_id"],
                          "info" if r.ok else "error", f"$ {command}\n{r.stdout}\n{r.stderr}")
        return r.as_dict()

    def list_files(self, computer_id: str, user_id: Optional[str], path: str) -> List[Dict[str, Any]]:
        row, p = self._with_provider(computer_id, user_id)
        return [f.as_dict() for f in p.list_files(computer_id, row["provider_ref"], path)]

    def read_file(self, computer_id: str, user_id: Optional[str], path: str) -> str:
        row, p = self._with_provider(computer_id, user_id)
        return p.read_file(computer_id, row["provider_ref"], path)

    def write_file(self, computer_id: str, user_id: Optional[str], path: str, content: str) -> bool:
        row, p = self._with_provider(computer_id, user_id)
        return p.write_file(computer_id, row["provider_ref"], path, content)

    def delete_file(self, computer_id: str, user_id: Optional[str], path: str) -> bool:
        row, p = self._with_provider(computer_id, user_id)
        return p.delete_file(computer_id, row["provider_ref"], path)

    def processes(self, computer_id: str, user_id: Optional[str]) -> List[Dict[str, Any]]:
        row, p = self._with_provider(computer_id, user_id)
        return [x.as_dict() for x in p.list_processes(computer_id, row["provider_ref"])]

    def stop_process(self, computer_id: str, user_id: Optional[str], pid: str) -> bool:
        row, p = self._with_provider(computer_id, user_id)
        return p.stop_process(computer_id, row["provider_ref"], pid)

    def resources(self, computer_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        row, p = self._with_provider(computer_id, user_id)
        raw = p.resources(computer_id, row["provider_ref"])
        import database

        conn = database.conn()
        conn.execute("INSERT INTO resource_metrics(computer_id,user_id,raw,ts) VALUES(?,?,?,?)",
                     (computer_id, row["user_id"], json.dumps(raw, default=str), time.time()))
        conn.commit()
        return raw

    def browser(self, computer_id: str, user_id: Optional[str], action: Dict[str, Any]) -> Dict[str, Any]:
        row, p = self._with_provider(computer_id, user_id)
        if not hasattr(p, "browser"):
            raise RuntimeError("selected provider does not support browser automation")
        return p.browser(computer_id, row["provider_ref"], action)

    def screenshot(self, computer_id: str, user_id: Optional[str]) -> Optional[str]:
        row, p = self._with_provider(computer_id, user_id)
        return p.screenshot(computer_id, row["provider_ref"])

    def create_job(self, computer_id: str, user_id: str, session_id: str = "") -> str:
        jid = f"job-{secrets.token_hex(8)}"
        store.save_job({"id": jid, "computer_id": computer_id, "user_id": user_id,
                        "session_id": session_id, "status": "running", "steps": []})
        return jid

    def job(self, job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return store.get_job(job_id, user_id)

    def sweep_temporary(self, max_age_seconds: Optional[int] = None) -> int:
        ttl = int(max_age_seconds or getattr(config, "COMPUTER_TEMP_TTL", 3600))
        removed = 0
        for c in store.list_computers(None, 1000):
            if c.get("mode") == "temporary" and (time.time() - float(c.get("created", 0))) > ttl:
                try:
                    if self.delete(c["id"], c["user_id"]):
                        removed += 1
                except Exception:
                    continue
        return removed


_manager: Optional[ComputerManager] = None


def get_manager() -> ComputerManager:
    global _manager
    if _manager is None:
        _manager = ComputerManager()
    return _manager
