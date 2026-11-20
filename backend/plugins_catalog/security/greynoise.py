from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class GreyNoisePlugin(BasePlugin):
    manifest = PluginManifest(
        id="greynoise",
        name="GreyNoise",
        description="Distinguish targeted attacks from internet noise",
        long_description="GreyNoise classifies IP addresses that are scanning the internet so you can filter out background noise and focus on real threats.",
        version="1.0.0",
        author="outcome",
        icon="🔍",
        category="security",
        tags=["threat-intel", "noise-reduction", "ip"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="greynoise.lookupIP",
                display_name="Lookup IP",
                description="Check if an IP is internet scanner noise or a targeted attacker",
                parameters={"ip": {"type": "string", "description": "IP address to look up"}},
            ),
            PluginTool(
                name="greynoise.contextIP",
                display_name="Get IP Context",
                description="Get full context for an IP: actor, tags, CVE references",
                parameters={"ip": {"type": "string"}},
            ),
            PluginTool(
                name="greynoise.riotLookup",
                display_name="RIOT Lookup",
                description="Check if IP belongs to a known benign service (Google, Cloudflare, etc)",
                parameters={"ip": {"type": "string"}},
            ),
            PluginTool(
                name="greynoise.gnqlQuery",
                display_name="Run GNQL Query",
                description="Run a GreyNoise Query Language search against the dataset",
                parameters={"query": {"type": "string", "description": "GNQL query string"}},
            ),
        ],
        website_url="https://www.greynoise.io",
        docs_url="https://docs.greynoise.io/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        api_key = self.credentials.get("api_key")
        headers = {"key": api_key, "Accept": "application/json"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            if tool_name == "greynoise.lookupIP":
                resp = await client.get(
                    f"https://api.greynoise.io/v3/community/{parameters['ip']}", headers=headers
                )
            elif tool_name == "greynoise.contextIP":
                resp = await client.get(
                    f"https://api.greynoise.io/v2/noise/context/{parameters['ip']}", headers=headers
                )
            elif tool_name == "greynoise.riotLookup":
                resp = await client.get(
                    f"https://api.greynoise.io/v2/riot/{parameters['ip']}", headers=headers
                )
            elif tool_name == "greynoise.gnqlQuery":
                resp = await client.get(
                    "https://api.greynoise.io/v2/experimental/gnql",
                    headers=headers,
                    params={"query": parameters["query"]},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code == 404:
                return {"found": False, "message": "No record for this indicator"}
            resp.raise_for_status()
            return resp.json()
