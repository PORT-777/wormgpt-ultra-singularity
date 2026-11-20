import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class SentinelPlugin(BasePlugin):
    manifest = PluginManifest(
        id="sentinel",
        name="Microsoft Sentinel",
        description="Query Sentinel and manage incidents",
        long_description="Microsoft Sentinel integration allows the agent to run KQL queries, manage security incidents, and create detection rules within your Sentinel workspace.",
        version="1.0.0",
        author="outcome",
        icon="🛡️",
        category="siem",
        tags=["siem", "microsoft", "incidents", "kql"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2"},
        tools=[
            PluginTool(name="sentinel.runKQL", description="Run KQL query against Sentinel", parameters={"workspace_id": {"type": "string"}, "query": {"type": "string"}}),
            PluginTool(name="sentinel.getIncidents", description="Get Sentinel security incidents", parameters={"workspace_id": {"type": "string"}}),
            PluginTool(name="sentinel.createRule", description="Create analytics detection rule", parameters={"workspace_id": {"type": "string"}, "name": {"type": "string"}, "query": {"type": "string"}}),
            PluginTool(name="sentinel.updateIncident", description="Update incident status/severity", parameters={"incident_id": {"type": "string"}, "status": {"type": "string"}, "severity": {"type": "string"}}),
            PluginTool(name="sentinel.getAlerts", description="Get security alerts", parameters={"workspace_id": {"type": "string"}}),
        ],
        website_url="https://azure.microsoft.com/en-us/products/microsoft-sentinel/",
        docs_url="https://learn.microsoft.com/en-us/azure/sentinel/rest-api-overview",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('access_token') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = self.credentials.get('access_token')
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            if tool_name == "sentinel.runKQL":
                workspace_id = parameters['workspace_id']
                url = f"https://management.azure.com/subscriptions/SUB_ID/resourceGroups/RG_ID/providers/Microsoft.OperationalInsights/workspaces/{workspace_id}/query?api-version=2021-12-01-preview"
                payload = {"query": parameters['query']}
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "sentinel.getIncidents":
                workspace_id = parameters['workspace_id']
                url = f"https://management.azure.com/subscriptions/SUB_ID/resourceGroups/RG_ID/providers/Microsoft.SecurityInsights/workspaces/{workspace_id}/incidents?api-version=2023-02-01"
                resp = await client.get(url, headers=headers)
            elif tool_name == "sentinel.createRule":
                workspace_id = parameters['workspace_id']
                url = f"https://management.azure.com/subscriptions/SUB_ID/resourceGroups/RG_ID/providers/Microsoft.SecurityInsights/workspaces/{workspace_id}/alertRules?api-version=2023-02-01"
                payload = {
                    "properties": {
                        "displayName": parameters['name'],
                        "query": parameters['query'],
                        "enabled": True
                    }
                }
                resp = await client.put(url, headers=headers, json=payload)
            elif tool_name == "sentinel.updateIncident":
                incident_id = parameters['incident_id']
                url = f"https://management.azure.com/subscriptions/SUB_ID/resourceGroups/RG_ID/providers/Microsoft.SecurityInsights/workspaces/WS_ID/incidents/{incident_id}?api-version=2023-02-01"
                payload = {"properties": {"status": parameters.get('status'), "severity": parameters.get('severity')}}
                resp = await client.patch(url, headers=headers, json=payload)
            elif tool_name == "sentinel.getAlerts":
                workspace_id = parameters['workspace_id']
                url = f"https://management.azure.com/subscriptions/SUB_ID/resourceGroups/RG_ID/providers/Microsoft.SecurityInsights/workspaces/{workspace_id}/alerts?api-version=2023-02-01"
                resp = await client.get(url, headers=headers)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
