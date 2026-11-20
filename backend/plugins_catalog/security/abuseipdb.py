import json
from typing import Dict, Any
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin
import httpx

@register_plugin
class AbuseIPDBPlugin(BasePlugin):
    manifest = PluginManifest(
        id="abuseipdb",
        name="AbuseIPDB",
        description="IP address abuse reporting and lookup",
        long_description="AbuseIPDB is a centralized database of IP addresses that have been reported for abusive behavior, such as hacking, spamming, and DDoS attacks.",
        version="1.0.0",
        author="outcome",
        icon="🚫",
        category="security",
        tags=["threat-intel", "ip-reputation", "abuse"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="abuseipdb.check", 
                display_name="Check IP Abuse Score",
                description="Check IP abuse confidence score and report details",
                parameters={"ipAddress": {"type": "string", "description": "The IP address to check"}},
                requires_auth=True
            ),
            PluginTool(
                name="abuseipdb.report", 
                display_name="Report Abusive IP",
                description="Report an abusive IP address to the database",
                parameters={
                    "ipAddress": {"type": "string"},
                    "comment": {"type": "string", "description": "Reason for reporting"}
                },
                requires_auth=True
            ),
            PluginTool(
                name="abuseipdb.blacklist", 
                display_name="Get Blacklist",
                description="Get current blacklist of abusive IPs",
                parameters={},
                requires_auth=True
            ),
        ],
        website_url="https://www.abuseipdb.com",
        docs_url="https://www.abuseipdb.com/api",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('api_key') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        api_key = self.credentials.get('api_key')
        headers = {"Key": api_key, "Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            if tool_name == "abuseipdb.check":
                url = "https://api.abuseipdb.com/api/v2/check"
                params = {"ipAddress": parameters['ipAddress']}
                resp = await client.get(url, headers=headers, params=params)
            elif tool_name == "abuseipdb.report":
                url = "https://api.abuseipdb.com/api/v2/report"
                data = {
                    "ipAddress": parameters['ipAddress'],
                    "comment": parameters['comment']
                }
                resp = await client.post(url, headers=headers, json=data)
            elif tool_name == "abuseipdb.blacklist":
                # AbuseIPDB doesn't have a simple 'blacklist' endpoint, 
                # but we can simulate a search for high-confidence IPs
                url = "https://api.abuseipdb.com/api/v2/blacklist"
                resp = await client.get(url, headers=headers)
            else:
                raiseValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
