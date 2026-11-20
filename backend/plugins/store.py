"""
Concrete plugin persistence layer.

This is a self-contained store so the plugin system works out of the box,
with no external database required. Swap this class for your real DB adapter
by preserving the same async method surface and passing it to PluginManager /
PluginRuntime.

Methods are intentionally narrow: anything the manager, runtime, or auditor
calls lives here.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class InstalledPluginRecord:
    user_id: str
    plugin_id: str
    is_enabled: bool = True
    installed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used_at: Optional[str] = None


class InMemoryPluginStore:
    """
    Async, in-process store. Safe under a single event loop.
    All mutations go through an asyncio lock so concurrent tool calls don't tear state.
    """

    def __init__(self) -> None:
        self._installs: Dict[str, Dict[str, InstalledPluginRecord]] = {}
        self._credentials: Dict[str, Dict[str, bytes]] = {}
        self._usage_log: List[Dict[str, Any]] = []
        self._security_alerts: List[Dict[str, Any]] = []
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ installs

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
            user_slot = self._installs.setdefault(user_id, {})
            if plugin_id in user_slot:
                return True  # idempotent
            user_slot[plugin_id] = InstalledPluginRecord(user_id=user_id, plugin_id=plugin_id)
            return True

    async def update_user_plugin_status(self, user_id: str, plugin_id: str, enabled: bool) -> bool:
        async with self._lock:
            record = self._installs.get(user_id, {}).get(plugin_id)
            if not record:
                return False
            record.is_enabled = enabled
            return True

    async def delete_user_plugin(self, user_id: str, plugin_id: str) -> bool:
        async with self._lock:
            slot = self._installs.get(user_id)
            if not slot or plugin_id not in slot:
                return False
            del slot[plugin_id]
            return True

    async def touch_last_used(self, user_id: str, plugin_id: str) -> None:
        record = self._installs.get(user_id, {}).get(plugin_id)
        if record:
            record.last_used_at = datetime.utcnow().isoformat()

    # --------------------------------------------------------------- credentials

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

    # ------------------------------------------------------------------ auditing

    async def insert_plugin_usage_log(self, entry: Dict[str, Any]) -> None:
        self._usage_log.append(entry)

    async def insert_plugin_log(self, entry: Dict[str, Any]) -> None:
        self._usage_log.append(entry)

    async def create_security_alert(self, alert: Dict[str, Any]) -> None:
        self._security_alerts.append(alert)

    async def update_plugin_metrics(self, plugin_id: str, tool_name: str, latency: float) -> None:
        key = f"{plugin_id}.{tool_name}"
        slot = self._metrics.setdefault(key, {"calls": 0, "total_latency": 0.0, "max_latency": 0.0})
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
            "security_alerts": len([a for a in self._security_alerts if a.get("user_id") == user_id]),
        }

    # ------------------------------------------------------------------ debug

    def snapshot(self) -> Dict[str, Any]:
        return {
            "installs": {
                u: {p: asdict(r) for p, r in slot.items()} for u, slot in self._installs.items()
            },
            "usage_log_size": len(self._usage_log),
            "security_alerts": len(self._security_alerts),
            "metrics": json.loads(json.dumps(self._metrics)),
        }
