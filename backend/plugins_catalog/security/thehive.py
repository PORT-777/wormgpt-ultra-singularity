from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class TheHivePlugin(BasePlugin):
    manifest = PluginManifest(
        id="thehive",
        name="TheHive",
        description="Security incident response platform",
        long_description="TheHive is a scalable case management platform for SOC teams. Create cases, attach observables, and track investigation tasks.",
        version="1.0.0",
        author="outcome",
        icon="🐝",
        category="security",
        tags=["incident-response", "case-management", "soar"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "url_field": "thehive_url"},
        tools=[
            PluginTool(
                name="thehive.createCase",
                display_name="Create Case",
                description="Create a new incident case",
                parameters={
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "integer", "description": "1-4, 4 = critical"},
                },
            ),
            PluginTool(
                name="thehive.addObservable",
                display_name="Add Observable",
                description="Add an IOC as an observable to a case",
                parameters={
                    "case_id": {"type": "string"},
                    "data_type": {"type": "string", "description": "ip, domain, hash, url"},
                    "data": {"type": "string"},
                    "message": {"type": "string"},
                },
            ),
            PluginTool(
                name="thehive.addTask",
                display_name="Add Task",
                description="Add an investigation task to a case",
                parameters={"case_id": {"type": "string"}, "title": {"type": "string"}},
            ),
            PluginTool(
                name="thehive.searchCases",
                display_name="Search Cases",
                description="Search existing cases with a query",
                parameters={"query": {"type": "string"}},
            ),
            PluginTool(
                name="thehive.updateCase",
                display_name="Update Case",
                description="Update case status or severity",
                parameters={
                    "case_id": {"type": "string"},
                    "status": {"type": "string"},
                    "severity": {"type": "integer"},
                },
            ),
            PluginTool(
                name="thehive.addLog",
                display_name="Add Log",
                description="Add an investigation log entry to a task",
                parameters={"task_id": {"type": "string"}, "message": {"type": "string"}},
            ),
        ],
        website_url="https://thehive-project.org",
        docs_url="https://docs.strangebee.com/thehive/api-docs/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key")) and bool(self.credentials.get("thehive_url"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['api_key']}",
            "Content-Type": "application/json",
        }

    @property
    def _base(self) -> str:
        return self.credentials["thehive_url"].rstrip("/") + "/api/v1"

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            if tool_name == "thehive.createCase":
                payload = {
                    "title": parameters["title"],
                    "description": parameters.get("description", ""),
                    "severity": parameters.get("severity", 2),
                    "tlp": 2,
                    "pap": 2,
                }
                resp = await client.post(f"{self._base}/case", headers=self._headers, json=payload)
            elif tool_name == "thehive.addObservable":
                payload = {
                    "dataType": parameters["data_type"],
                    "data": parameters["data"],
                    "message": parameters.get("message", ""),
                    "tlp": 2,
                    "pap": 2,
                }
                resp = await client.post(
                    f"{self._base}/case/{parameters['case_id']}/observable",
                    headers=self._headers,
                    json=payload,
                )
            elif tool_name == "thehive.addTask":
                payload = {"title": parameters["title"], "status": "Waiting"}
                resp = await client.post(
                    f"{self._base}/case/{parameters['case_id']}/task",
                    headers=self._headers,
                    json=payload,
                )
            elif tool_name == "thehive.searchCases":
                payload = {"query": [{"_name": "listCase"}], "filter": parameters.get("query")}
                resp = await client.post(f"{self._base}/case/_search", headers=self._headers, json=payload)
            elif tool_name == "thehive.updateCase":
                payload: Dict[str, Any] = {}
                if parameters.get("status"):
                    payload["status"] = parameters["status"]
                if parameters.get("severity"):
                    payload["severity"] = parameters["severity"]
                resp = await client.patch(
                    f"{self._base}/case/{parameters['case_id']}",
                    headers=self._headers,
                    json=payload,
                )
            elif tool_name == "thehive.addLog":
                payload = {"message": parameters["message"]}
                resp = await client.post(
                    f"{self._base}/task/{parameters['task_id']}/log",
                    headers=self._headers,
                    json=payload,
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "ok"}
