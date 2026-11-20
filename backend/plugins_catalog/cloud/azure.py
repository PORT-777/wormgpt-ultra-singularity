import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class AzurePlugin(BasePlugin):
    manifest = PluginManifest(
        id="azure",
        name="Microsoft Azure",
        description="Query Azure security and activity logs",
        long_description="Azure integration allows the agent to query Activity Logs, Defender for Cloud alerts, and Microsoft Sentinel incidents using Azure SDK/REST APIs.",
        version="1.0.0",
        author="outcome",
        icon="🟦",
        category="cloud",
        tags=["cloud", "azure", "microsoft", "security"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2"},
        tools=[
            PluginTool(name="azure.activityLogs", description="Query Azure Activity Log", parameters={"subscription_id": {"type": "string"}, "filter": {"type": "string"}}),
            PluginTool(name="azure.defenderAlerts", description="Get Defender for Cloud alerts", parameters={"subscription_id": {"type": "string"}}),
            PluginTool(name="azure.sentinelIncidents", description="Get Microsoft Sentinel incidents", parameters={"workspace_id": {"type": "string"}}),
            PluginTool(name="azure.aadSignins", description="Get Azure AD sign-in logs", parameters={"subscription_id": {"type": "string"}}),
            PluginTool(name="azure.resourceInventory", description="List Azure resources", parameters={"subscription_id": {"type": "string"}}),
        ],
        website_url="https://azure.microsoft.com",
        docs_url="https://learn.microsoft.com/en-us/rest/api/azure/",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('access_token') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = self.credentials.get('access_token')
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            if tool_name == "azure.activityLogs":
                # Azure Monitor REST API for Activity Logs
                sub_id = parameters['subscription_id']
                url = f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.Insights/activityLogs?api-version=2015-04-01"
                resp = await client.get(url, headers=headers)
            elif tool_name == "azure.defenderAlerts":
                sub_id = parameters['subscription_id']
                url = f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.Security/alerts?api-version=2021-06-01"
                resp = await client.get(url, headers=headers)
            elif tool_name == "azure.sentinelIncidents":
                ws_id = parameters['workspace_id']
                url = f"https://management.azure.com/subscriptions/SUB_ID/resourceGroups/RG_ID/providers/Microsoft.OperationalInsights/workspaces/{ws_id}/providers/Microsoft.SecurityInsights/incidents?api-version=2023-02-01"
                # Note: subscription/rg_id would typically be part of credentials or context
                resp = await client.get(url, headers=headers)
            elif tool_name == "azure.aadSignins":
                # Microsoft Graph API
                url = "https://graph.microsoft.com/v1.0/auditLogs/signIns"
                resp = await client.get(url, headers=headers)
            elif tool_name == "azure.resourceInventory":
                sub_id = parameters['subscription_id']
                url = f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.Resources/resources?api-version=2021-04-01"
                resp = await client.get(url, headers=headers)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
