from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class DatadogPlugin(BasePlugin):
    manifest = PluginManifest(
        id="datadog",
        name="Datadog",
        description="Metrics, monitors, events and dashboards",
        long_description=(
            "Query timeseries metrics with the v1 query API, list and mute monitors, "
            "post deployment or incident events to the event stream and enumerate "
            "dashboards. Requires an API key plus an application key."
        ),
        version="1.0.0",
        author="outcome",
        icon="🐶",
        category="devops",
        tags=["devops", "datadog", "metrics", "monitoring", "observability"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "extra_fields": ["app_key", "site"]},
        tools=[
            PluginTool(
                name="datadog.queryMetrics",
                display_name="Query Metrics",
                description="Run a metrics query over a time window",
                parameters={
                    "query": {"type": "string", "description": "e.g. avg:system.cpu.user{*}"},
                    "from": {"type": "integer", "description": "Unix timestamp"},
                    "to": {"type": "integer", "description": "Unix timestamp"},
                },
            ),
            PluginTool(
                name="datadog.listMonitors",
                display_name="List Monitors",
                description="List monitors with status and type",
                parameters={"group_states": {"type": "string", "description": "alert,warn,no data,ok"}},
            ),
            PluginTool(
                name="datadog.muteMonitor",
                display_name="Mute Monitor",
                description="Mute all scopes of a monitor (or unmute)",
                parameters={"monitor_id": {"type": "string"}, "scope": {"type": "string"}},
            ),
            PluginTool(
                name="datadog.postEvent",
                display_name="Post Event",
                description="Send an event to the Datadog event stream",
                parameters={
                    "title": {"type": "string"},
                    "text": {"type": "string"},
                    "alert_type": {"type": "string", "description": "info | warning | error | success"},
                    "tags": {"type": "array"},
                },
            ),
            PluginTool(
                name="datadog.listDashboards",
                display_name="List Dashboards",
                description="List dashboards with titles and urls",
                parameters={},
            ),
        ],
        website_url="https://www.datadoghq.com",
        docs_url="https://docs.datadoghq.com/api/",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key")) and bool(self.credentials.get("app_key"))

    @property
    def _base(self) -> str:
        site = (self.credentials.get("site") or "datadoghq.com").strip("/")
        return f"https://api.{site}"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "DD-API-KEY": self.credentials["api_key"],
            "DD-APPLICATION-KEY": self.credentials["app_key"],
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        import time
        now = int(time.time())
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "datadog.queryMetrics":
                resp = await client.get(
                    f"{self._base}/api/v1/query",
                    headers=self._headers,
                    params={
                        "query": parameters.get("query", ""),
                        "from": int(parameters.get("from") or now - 3600),
                        "to": int(parameters.get("to") or now),
                    },
                )
            elif tool_name == "datadog.listMonitors":
                resp = await client.get(
                    f"{self._base}/api/v1/monitor",
                    headers=self._headers,
                    params={"group_states": parameters.get("group_states") or "alert,warn,no data,ok"},
                )
            elif tool_name == "datadog.muteMonitor":
                resp = await client.post(
                    f"{self._base}/api/v1/monitor/{parameters['monitor_id']}/mute",
                    headers=self._headers,
                    params={"scope": parameters.get("scope") or "*"},
                )
            elif tool_name == "datadog.postEvent":
                resp = await client.post(
                    f"{self._base}/api/v1/events",
                    headers=self._headers,
                    json={
                        "title": parameters.get("title", ""),
                        "text": parameters.get("text", ""),
                        "alert_type": parameters.get("alert_type") or "info",
                        "tags": parameters.get("tags") or [],
                    },
                )
            elif tool_name == "datadog.listDashboards":
                resp = await client.get(
                    f"{self._base}/api/v1/dashboard", headers=self._headers
                )
            else:
                raise ValueError(f"Unknown datadog tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Datadog HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
