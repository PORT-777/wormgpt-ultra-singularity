from typing import Any, Dict, List, Optional
import json
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import PLUGIN_REGISTRY, get_plugin_from_registry
import httpx

@register_plugin
class ShodanPlugin(BasePlugin):
    manifest = PluginManifest(
        id="shodan",
        name="Shodan",
        description="Search engine for internet-connected devices",
        long_description="Shodan is a search engine for internet-connected devices. It allows you to find specific devices, services, and vulnerabilities across the globe.",
        version="1.0.0",
        author="outcome",
        icon="🌐",
        category="security",
        tags=["osint", "network", "infrastructure", "iot"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(name="shodan.hostLookup", description="Get all info about an IP address", parameters={"ip": {"type": "string"}}),
            PluginTool(name="shodan.search", description="Search Shodan for specific services/banners", parameters={"query": {"type": "string"}}),
            PluginTool(name="shodan.dnsLookup", description="DNS lookup using Shodan", parameters={"hostname": {"type": "string"}}),
            PluginTool(name="shodan.reverseDNS", description="Reverse DNS lookup for IP", parameters={"ip": {"type": "string"}}),
            PluginTool(name="shodan.getMyIP", description="Get current public IP", parameters={}),
            PluginTool(name="shodan.exploitSearch", description="Search for exploits related to CVE or software", parameters={"query": {"type": "string"}}),
        ],
        website_url="https://www.shodan.io",
        docs_url="https://developer.shodan.io/",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('api_key') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        api_key = self.credentials.get('api_key')
        params = {"key": api_key}
        
        async with httpx.AsyncClient() as client:
            if tool_name == "shodan.hostLookup":
                url = f"https://api.shodan.io/shodan/host/{parameters['ip']}"
                resp = await client.get(url, params=params)
            elif tool_name == "shodan.search":
                url = f"https://api.shodan.io/shodan/host/search"
                resp = await client.get(url, params={**params, "query": parameters['query']})
            elif tool_name == "shodan.dnsLookup":
                url = f"https://api.shodan.io/dns/resolver?hostname={parameters['hostname']}"
                resp = await client.get(url, params=params)
            elif tool_name == "shodan.reverseDNS":
                url = f"https://api.shodan.io/dns/resolver?hostname={parameters['ip']}" # Simplified
                resp = await client.get(url, params=params)
            elif tool_name == "shodan.getMyIP":
                url = "https://api.shodan.io/host/myip"
                resp = await client.get(url, params=params)
            elif tool_name == "shodan.exploitSearch":
                url = f"https://api.shodan.io/shodan/host/search"
                resp = await client.get(url, params={**params, "query": parameters['query']})
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
