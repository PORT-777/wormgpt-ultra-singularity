from typing import Any, Dict, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class WazuhPlugin(BasePlugin):
    manifest = PluginManifest(
        id="wazuh",
        name="Wazuh",
        description="Agents, alerts and manager health from the Wazuh API",
        long_description=(
            "Authenticates against the Wazuh manager API (port 55000), caches the JWT, "
            "then lists agents and their status, queries alerts and vulnerabilities, "
            "and reads cluster/manager health."
        ),
        version="1.0.0",
        author="outcome",
        icon="🛰️",
        category="siem",
        tags=["siem", "wazuh", "hids", "alerts", "agents"],
        auth_type="apikey",
        auth_config={
            "api_key_field": "password",
            "extra_fields": ["url", "username"],
        },
        tools=[
            PluginTool(
                name="wazuh.listAgents",
                display_name="List Agents",
                description="List agents with status, version and last keep-alive",
                parameters={
                    "status": {"type": "string", "description": "active | disconnected | pending"},
                    "limit": {"type": "integer", "description": "Default 100"},
                },
            ),
            PluginTool(
                name="wazuh.getAlerts",
                display_name="Alerts",
                description="Query alerts with optional filters and time window",
                parameters={
                    "limit": {"type": "integer", "description": "Default 50"},
                    "agent_id": {"type": "string"},
                    "min_level": {"type": "integer", "description": "Rule level floor"},
                },
            ),
            PluginTool(
                name="wazuh.getVulnerabilities",
                display_name="Vulnerabilities",
                description="List vulnerabilities detected on an agent",
                parameters={"agent_id": {"type": "string"}, "limit": {"type": "integer"}},
            ),
            PluginTool(
                name="wazuh.managerInfo",
                display_name="Manager Info",
                description="Read manager version, cluster status and daemon states",
                parameters={},
            ),
            PluginTool(
                name="wazuh.activeResponse",
                display_name="Active Response",
                description="Run an active-response command on an agent",
                parameters={
                    "agent_id": {"type": "string"},
                    "command": {"type": "string", "description": "e.g. firewall-drop0"},
                    "arguments": {"type": "array"},
                },
            ),
        ],
        website_url="https://wazuh.com",
        docs_url="https://documentation.wazuh.com/current/user-manual/api/reference.html",
        is_free=True,
        is_official=True,
    )

    def __init__(self, credentials: Dict[str, Any]):
        self._token: Optional[str] = None
        super().__init__(credentials)

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("url")) and bool(
            self.credentials.get("username")
        ) and bool(self.credentials.get("password"))

    @property
    def _base(self) -> str:
        raw = self.credentials["url"].strip().rstrip("/")
        if not raw.startswith("http"):
            raw = "https://" + raw
        if ":" not in raw.split("//")[-1]:
            raw = raw + ":55000"
        return raw

    async def _auth_headers(self) -> Dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.post(
                f"{self._base}/security/user/authenticate",
                auth=(self.credentials["username"], self.credentials["password"]),
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Wazuh auth HTTP {resp.status_code}: {resp.text[:300]}")
            self._token = resp.json().get("data", {}).get("token", "")
        return {"Authorization": f"Bearer {self._token}"}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            if tool_name == "wazuh.listAgents":
                params: Dict[str, Any] = {
                    "limit": min(int(parameters.get("limit") or 100), 500)
                }
                if parameters.get("status"):
                    params["status"] = parameters["status"]
                resp = await client.get(
                    f"{self._base}/agents", headers=headers, params=params
                )
            elif tool_name == "wazuh.getAlerts":
                params = {"limit": min(int(parameters.get("limit") or 50), 500)}
                if parameters.get("agent_id"):
                    params["agents_list"] = parameters["agent_id"]
                if parameters.get("min_level") is not None:
                    params["rule.level"] = f">{int(parameters['min_level']) - 1}"
                resp = await client.get(
                    f"{self._base}/alerts", headers=headers, params=params
                )
            elif tool_name == "wazuh.getVulnerabilities":
                resp = await client.get(
                    f"{self._base}/vulnerability/{parameters['agent_id']}",
                    headers=headers,
                    params={"limit": min(int(parameters.get("limit") or 50), 500)},
                )
            elif tool_name == "wazuh.managerInfo":
                info = await client.get(f"{self._base}/manager/info", headers=headers)
                status = await client.get(f"{self._base}/manager/status", headers=headers)
                if info.status_code >= 400:
                    raise RuntimeError(
                        f"Wazuh HTTP {info.status_code}: {info.text[:300]}"
                    )
                return {
                    "info": info.json().get("data", {}),
                    "status": status.json().get("data", {}) if status.status_code < 400 else {},
                }
            elif tool_name == "wazuh.activeResponse":
                resp = await client.put(
                    f"{self._base}/active-response",
                    headers=headers,
                    params={"agents_list": parameters["agent_id"]},
                    json={
                        "command": parameters["command"],
                        "arguments": parameters.get("arguments") or [],
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code == 401:
                self._token = None
                raise RuntimeError("Wazuh token expired — retry the call")
            if resp.status_code >= 400:
                raise RuntimeError(f"Wazuh HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
