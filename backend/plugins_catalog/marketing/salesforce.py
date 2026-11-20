from typing import Any, Dict

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

API_VERSION = "v60.0"


@register_plugin
class SalesforcePlugin(BasePlugin):
    manifest = PluginManifest(
        id="salesforce",
        name="Salesforce",
        description="Run SOQL queries and manage Salesforce records",
        long_description=(
            "Salesforce REST API with an OAuth access token: run SOQL queries, "
            "list sObjects, and read/create/update records. The instance URL is "
            "discovered automatically during authorization."
        ),
        version="1.0.0",
        author="outcome",
        icon="☁️",
        category="marketing",
        tags=["marketing", "crm", "salesforce", "soql", "records"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="salesforce.query",
                description="Run a SOQL query",
                parameters={"soql": {"type": "string"}},
            ),
            PluginTool(
                name="salesforce.listObjects",
                description="List available sObjects",
                parameters={},
            ),
            PluginTool(
                name="salesforce.getRecord",
                description="Fetch one record",
                parameters={
                    "sobject": {"type": "string"},
                    "record_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="salesforce.createRecord",
                description="Create a record",
                parameters={
                    "sobject": {"type": "string"},
                    "fields": {"type": "object"},
                },
            ),
            PluginTool(
                name="salesforce.updateRecord",
                description="Update a record",
                parameters={
                    "sobject": {"type": "string"},
                    "record_id": {"type": "string"},
                    "fields": {"type": "object"},
                },
            ),
        ],
        website_url="https://www.salesforce.com",
        docs_url="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _instance(self) -> str:
        instance = (
            self.credentials.get("instance_url")
            or self.credentials.get("salesforce_instance_url")
            or ""
        )
        if not instance:
            raise ValueError(
                "Salesforce instance_url is missing. Reconnect the integration."
            )
        return str(instance).rstrip("/")

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        base = f"{self._instance}/services/data/{API_VERSION}"
        headers = self._headers
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "salesforce.query":
                resp = await client.get(
                    f"{base}/query",
                    headers=headers,
                    params={"q": parameters["soql"]},
                )
            elif tool_name == "salesforce.listObjects":
                resp = await client.get(f"{base}/sobjects", headers=headers)
            elif tool_name == "salesforce.getRecord":
                resp = await client.get(
                    f"{base}/sobjects/{parameters['sobject']}/{parameters['record_id']}",
                    headers=headers,
                )
            elif tool_name == "salesforce.createRecord":
                resp = await client.post(
                    f"{base}/sobjects/{parameters['sobject']}",
                    headers=headers,
                    json=parameters.get("fields") or {},
                )
            elif tool_name == "salesforce.updateRecord":
                resp = await client.patch(
                    f"{base}/sobjects/{parameters['sobject']}/{parameters['record_id']}",
                    headers=headers,
                    json=parameters.get("fields") or {},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            if resp.status_code == 204 or not resp.content:
                return {"status": "ok"}
            return resp.json()
