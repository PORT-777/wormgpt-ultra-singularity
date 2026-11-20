import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class SplunkPlugin(BasePlugin):
    manifest = PluginManifest(
        id="splunk",
        name="Splunk",
        description="Run searches and get alerts from Splunk",
        long_description="Splunk integration allows the agent to execute SPL queries, retrieve recent alerts, and look up IOCs directly within your Splunk enterprise or cloud environment.",
        version="1.0.0",
        author="outcome",
        icon="📈",
        category="siem",
        tags=["siem", "logs", "search", "alerts"],
        auth_type="apikey",
        auth_config={"api_key_field": "splunk_token", "host_field": "splunk_host"},
        tools=[
            PluginTool(name="splunk.search", description="Run SPL search query", parameters={"host": {"type": "string"}, "query": {"type": "string"}}),
            PluginTool(name="splunk.getAlerts", description="Get recent Splunk alerts", parameters={"host": {"type": "string"}}),
            PluginTool(name="splunk.createAlert", description="Create new Splunk alert rule", parameters={"host": {"type": "string"}, "name": {"type": "string"}, "query": {"type": "string"}}),
            PluginTool(name="splunk.getEvents", description="Get events matching criteria", parameters={"host": {"type": "string"}, "query": {"type": "string"}}),
            PluginTool(name="splunk.lookupIOC", description="Lookup IOC across all Splunk data", parameters={"host": {"type": "string"}, "ioc": {"type": "string"}}),
        ],
        website_url="https://www.splunk.com",
        docs_url="https://docs.splunk.com/Documentation/Splunk/latest/REST/RESToverview",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('splunk_token') is not None and self.credentials.get('splunk_host') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        host = parameters.get('host') or self.credentials.get('splunk_host')
        token = self.credentials.get('splunk_token')
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        base_url = f"https://{host}:8089/services"
        
        async with httpx.AsyncClient(verify=False) as client: # verify=False for self-signed certs common in Splunk
            if tool_name == "splunk.search":
                url = f"{base_url}/search/jobs"
                payload = {"search": parameters['query'], "output_mode": "json"}
                resp = await client.post(url, headers=headers, data=payload)
            elif tool_name == "splunk.getAlerts":
                url = f"{base_url}/alerts"
                resp = await client.get(url, headers=headers)
            elif tool_name == "splunk.createAlert":
                url = f"{base_url}/alerts"
                payload = {
                    "title": parameters['name'],
                    "search": parameters['query']
                }
                resp = await client.post(url, headers=headers, data=payload)
elif tool_name == "splunk.getEvents":
                url = f"{base_url}/search/jobs"
                payload = {"search": parameters['query'], "output_mode": "json"}
                resp = await client.post(url, headers=headers, data=payload)
            elif tool_name == "splunk.lookupIOC":
                # Simulated SPL search for IOC
                query = f"index=* \"{parameters['ioc']}\""
                url = f"{base_url}/search/jobs"
                payload = {"search": query, "output_mode": "json"}
                resp = await client.post(url, headers=headers, data=payload)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
