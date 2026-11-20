"""Splunk plugin — real REST calls against the Splunk management port."""
from __future__ import annotations

import asyncio
from typing import Any, Dict
from urllib.parse import urlsplit

import httpx

from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class SplunkPlugin(BasePlugin):
    manifest = PluginManifest(
        id="splunk",
        name="Splunk",
        description="Run searches and manage alerts in Splunk",
        long_description="Execute SPL searches, poll jobs, retrieve results and manage saved searches through the Splunk REST API.",
        version="2.0.0",
        author="PORT 777",
        icon="splunk",
        category="siem",
        tags=["siem", "logs", "search", "alerts"],
        auth_type="apikey",
        auth_config={"api_key_field": "splunk_token", "host_field": "splunk_host"},
        tools=[
            PluginTool(name="splunk.search", description="Run an SPL search and return results",
                       parameters={"query": {"type": "string"}, "max_results": {"type": "integer"}}),
            PluginTool(name="splunk.getAlerts", description="List fired alerts",
                       parameters={"count": {"type": "integer"}}),
            PluginTool(name="splunk.createAlert", description="Create a saved search alert",
                       parameters={"name": {"type": "string"}, "query": {"type": "string"}, "alert_actions": {"type": "string"}}),
            PluginTool(name="splunk.getEvents", description="Get events matching a query",
                       parameters={"query": {"type": "string"}, "count": {"type": "integer"}}),
            PluginTool(name="splunk.lookupIOC", description="Search the last 7 days for an IOC",
                       parameters={"ioc": {"type": "string"}}),
        ],
        website_url="https://www.splunk.com",
        docs_url="https://docs.splunk.com/Documentation/Splunk/latest/REST/RESToverview",
        is_free=True,
        is_official=True,
    )

    def __init__(self, credentials: Dict[str, Any] | None = None):
        super().__init__(credentials or {})
        token = self.credentials.get("splunk_token")
        host = self.credentials.get("splunk_host")
        if not token or not host:
            raise ValueError("splunk_token and splunk_host are required")
        self._verify_tls = str(self.credentials.get("allow_insecure_tls", "")).lower() not in {"1", "true", "yes"}

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("splunk_token") and self.credentials.get("splunk_host"))

    @staticmethod
    def _host_from(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            raise ValueError("splunk_host is required")
        if "://" not in raw:
            raw = "https://" + raw
        parts = urlsplit(raw)
        scheme = parts.scheme or "https"
        netloc = parts.netloc or parts.path.split("/")[0]
        if not netloc:
            raise ValueError("invalid splunk_host")
        if ":" not in netloc and scheme == "https":
            netloc += ":8089"
        elif ":" not in netloc and scheme == "http":
            netloc += ":8000"
        return f"{scheme}://{netloc}"

    @property
    def _base(self) -> str:
        return self._host_from(str(self.credentials.get("splunk_host", ""))).rstrip("/")

    def _headers(self) -> Dict[str, str]:
        token = str(self.credentials.get("splunk_token", ""))
        scheme = "Bearer" if token.startswith("eyJ") else "Splunk"
        return {"Authorization": f"{scheme} {token}", "Content-Type": "application/x-www-form-urlencoded"}

    async def _search(self, client: httpx.AsyncClient, query: str, count: int = 50, earliest: str = "") -> Dict[str, Any]:
        form: Dict[str, str] = {"search": query, "output_mode": "json", "count": str(count)}
        if earliest:
            form["earliest_time"] = earliest
        created = await client.post(f"{self._base}/services/search/jobs", headers=self._headers(), data=form)
        created.raise_for_status()
        sid = str((created.json() or {}).get("sid") or "")
        if not sid:
            return {"count": 0, "results": []}
        for _ in range(40):
            status = await client.get(f"{self._base}/services/search/jobs/{sid}", headers=self._headers())
            status.raise_for_status()
            entry = (status.json() or {}).get("entry") or []
            content = entry[0].get("content", {}) if entry else {}
            if content.get("isDone") in (True, "true", "1") or content.get("dispatchState") in ("DONE", "SUCCESS"):
                break
            await asyncio.sleep(0.01)
        results = await client.get(
            f"{self._base}/services/search/jobs/{sid}/results",
            headers=self._headers(),
            params={"output_mode": "json", "count": str(count)},
        )
        results.raise_for_status()
        rows = (results.json() or {}).get("results") or []
        return {"count": len(rows), "results": rows}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        params = parameters or {}
        async with httpx.AsyncClient(verify=self._verify_tls) as client:
            if tool_name == "splunk.search":
                return await self._search(client, str(params.get("query", "")), int(params.get("max_results") or params.get("count") or 50))
            if tool_name == "splunk.getEvents":
                return await self._search(client, str(params.get("query", "")), int(params.get("count") or 50))
            if tool_name == "splunk.lookupIOC":
                ioc = str(params.get("ioc", "")).replace('"', '\\"')
                return await self._search(client, f'index=* "{ioc}"', 50, earliest="-7d")
            if tool_name == "splunk.getAlerts":
                resp = await client.get(
                    f"{self._base}/services/alerts/fired_alerts",
                    headers=self._headers(),
                    params={"output_mode": "json", "count": str(int(params.get("count") or 50))},
                )
                resp.raise_for_status()
                entries = (resp.json() or {}).get("entry") or []
                alerts = [{"name": e.get("name"), **(e.get("content") or {})} for e in entries]
                return {"alerts": alerts}
            if tool_name == "splunk.createAlert":
                form = {
                    "name": str(params.get("name", "")),
                    "search": "search " + str(params.get("query", "")).strip(),
                    "is_scheduled": "1",
                    "alert_actions": str(params.get("alert_actions") or ""),
                }
                resp = await client.post(f"{self._base}/services/saved/searches", headers=self._headers(), data=form)
                resp.raise_for_status()
                return {"status": "created", "name": form["name"]}
            raise ValueError(f"Unknown tool: {tool_name}")
