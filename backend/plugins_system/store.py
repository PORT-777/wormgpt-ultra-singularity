"""
Plugin persistence.

Two implementations, same async surface:

  * InMemoryPluginStore   — process-lifetime, zero deps, used by tests
  * JsonFilePluginStore   — atomic JSON persistence under backend/data/,
                            survives restarts. Credentials stay Fernet-encrypted
                            at rest and are stored base64-wrapped.

Swap in your SQL adapter by keeping the same method names.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PluginStore")


@dataclass
class InstalledPluginRecord:
    user_id: str
    plugin_id: str
    is_enabled: bool = True
    installed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used_at: Optional[str] = None


class InMemoryPluginStore:
    """Async, in-process store. Safe under a single event loop."""

    def __init__(self) -> None:
        self._installs: Dict[str, Dict[str, InstalledPluginRecord]] = {}
        self._credentials: Dict[str, Dict[str, bytes]] = {}
        self._usage_log: List[Dict[str, Any]] = []
        self._security_alerts: List[Dict[str, Any]] = []
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------------- installs

    async def get_user_plugins(
        self, user_id: str, enabled_only: bool = False
    ) -> List[InstalledPluginRecord]:
        records = list(self._installs.get(user_id, {}).values())
        if enabled_only:
            records = [r for r in records if r.is_enabled]
        return records

    async def get_user_plugin(self, user_id: str, plugin_id: str) -> Optional[InstalledPluginRecord]:
        return self._installs.get(user_id, {}).get(plugin_id)

    async def create_user_plugin(self, user_id: str, plugin_id: str) -> bool:
        async with self._lock:
            slot = self._installs.setdefault(user_id, {})
            if plugin_id not in slot:
                slot[plugin_id] = InstalledPluginRecord(user_id=user_id, plugin_id=plugin_id)
            return True

    async def update_user_plugin_status(self, user_id: str, plugin_id: str, enabled: bool) -> bool:
        async with self._lock:
            rec = self._installs.get(user_id, {}).get(plugin_id)
            if not rec:
                return False
            rec.is_enabled = enabled
            return True

    async def delete_user_plugin(self, user_id: str, plugin_id: str) -> bool:
        async with self._lock:
            slot = self._installs.get(user_id)
            if not slot or plugin_id not in slot:
                return False
            del slot[plugin_id]
            return True

    async def touch_last_used(self, user_id: str, plugin_id: str) -> None:
        rec = self._installs.get(user_id, {}).get(plugin_id)
        if rec:
            rec.last_used_at = datetime.utcnow().isoformat()

    # ------------------------------------------------------------- credentials

    async def get_plugin_credentials(self, user_id: str, plugin_id: str) -> Optional[bytes]:
        return self._credentials.get(user_id, {}).get(plugin_id)

    async def save_plugin_credentials(self, user_id: str, plugin_id: str, creds: bytes) -> bool:
        async with self._lock:
            self._credentials.setdefault(user_id, {})[plugin_id] = creds
            return True

    async def delete_plugin_credentials(self, user_id: str, plugin_id: str) -> bool:
        async with self._lock:
            slot = self._credentials.get(user_id)
            if slot and plugin_id in slot:
                del slot[plugin_id]
            return True

    # ---------------------------------------------------------------- auditing

    async def insert_plugin_usage_log(self, entry: Dict[str, Any]) -> None:
        self._usage_log.append(entry)

    async def insert_plugin_log(self, entry: Dict[str, Any]) -> None:
        self._usage_log.append(entry)

    async def create_security_alert(self, alert: Dict[str, Any]) -> None:
        self._security_alerts.append(alert)

    async def update_plugin_metrics(self, plugin_id: str, tool_name: str, latency: float) -> None:
        key = f"{plugin_id}.{tool_name}"
        slot = self._metrics.setdefault(
            key, {"calls": 0, "total_latency": 0.0, "max_latency": 0.0}
        )
        slot["calls"] += 1
        slot["total_latency"] += latency
        slot["max_latency"] = max(slot["max_latency"], latency)

    async def get_user_plugin_usage_summary(self, user_id: str) -> Dict[str, Any]:
        entries = [e for e in self._usage_log if e.get("user_id") == user_id]
        by_plugin: Dict[str, int] = {}
        failures = 0
        for e in entries:
            by_plugin[e["plugin_id"]] = by_plugin.get(e["plugin_id"], 0) + 1
            if e.get("status") == "error":
                failures += 1
        return {
            "user_id": user_id,
            "total_calls": len(entries),
            "failures": failures,
            "by_plugin": by_plugin,
            "security_alerts": len(
                [a for a in self._security_alerts if a.get("user_id") == user_id]
            ),
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "installs": {
                u: {p: asdict(r) for p, r in slot.items()} for u, slot in self._installs.items()
            },
            "usage_log_size": len(self._usage_log),
            "security_alerts": len(self._security_alerts),
            "metrics": dict(self._metrics),
        }


class JsonFilePluginStore(InMemoryPluginStore):
    """Same behaviour as the in-memory store, plus atomic JSON persistence."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    # ------------------------------------------------------------- persistence

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("plugin store unreadable (%s), starting empty: %s", self.path, exc)
            return

        for user_id, slot in (raw.get("installs") or {}).items():
            self._installs[user_id] = {
                pid: InstalledPluginRecord(**rec) for pid, rec in slot.items()
            }
        for user_id, slot in (raw.get("credentials") or {}).items():
            self._credentials[user_id] = {
                pid: base64.b64decode(blob) for pid, blob in slot.items()
            }
        self._usage_log = raw.get("usage_log") or []
        self._security_alerts = raw.get("security_alerts") or []
        self._metrics = raw.get("metrics") or {}
        logger.info("plugin store loaded: %d users, %d audit entries",
                    len(self._installs), len(self._usage_log))

    def _persist(self) -> None:
        payload = {
            "installs": {
                u: {p: asdict(r) for p, r in slot.items()} for u, slot in self._installs.items()
            },
            "credentials": {
                u: {p: base64.b64encode(blob).decode() for p, blob in slot.items()}
                for u, slot in self._credentials.items()
            },
            "usage_log": self._usage_log[-500:],  # bounded
            "security_alerts": self._security_alerts[-200:],
            "metrics": self._metrics,
        }
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # -------------------------------------------------- overrides that persist

    async def create_user_plugin(self, user_id: str, plugin_id: str) -> bool:
        ok = await super().create_user_plugin(user_id, plugin_id)
        self._persist()
        return ok

    async def update_user_plugin_status(self, user_id: str, plugin_id: str, enabled: bool) -> bool:
        ok = await super().update_user_plugin_status(user_id, plugin_id, enabled)
        if ok:
            self._persist()
        return ok

    async def delete_user_plugin(self, user_id: str, plugin_id: str) -> bool:
        ok = await super().delete_user_plugin(user_id, plugin_id)
        if ok:
            self._persist()
        return ok

    async def save_plugin_credentials(self, user_id: str, plugin_id: str, creds: bytes) -> bool:
        ok = await super().save_plugin_credentials(user_id, plugin_id, creds)
        if ok:
            self._persist()
        return ok

    async def delete_plugin_credentials(self, user_id: str, plugin_id: str) -> bool:
        ok = await super().delete_plugin_credentials(user_id, plugin_id)
        if ok:
            self._persist()
        return ok

    async def insert_plugin_usage_log(self, entry: Dict[str, Any]) -> None:
        await super().insert_plugin_usage_log(entry)
        self._persist()

    async def create_security_alert(self, alert: Dict[str, Any]) -> None:
        await super().create_security_alert(alert)
        self._persist()
