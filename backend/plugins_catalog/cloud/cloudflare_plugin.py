from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class CloudflarePlugin(BasePlugin):
    manifest = PluginManifest(
        id="cloudflare",
        name="Cloudflare",
        description="Manage DNS, Cache, and WAF",
        long_description=(
            "Complete Cloudflare management: list zones, manage DNS records, "
            "purge edge cache, and inspect firewall rules."
        ),
        version="1.0.0",
        author="outcome",
        icon="🌩️",
        category="cloud",
        tags=["cloud", "cloudflare", "dns", "waf", "cdn"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_token"},
        tools=[
            PluginTool(
                name="cloudflare.listZones",
                display_name="List Zones",
                description="List all Cloudflare zones",
                parameters={},
            ),
            PluginTool(
                name="cloudflare.dnsRecords",
                display_name="DNS Records",
                description="List DNS records for a zone",
                parameters={
                    "zone_id": {"type": "string"},
                    "type": {"type": "string", "description": "A | AAAA | CNAME | TXT"},
                },
            ),
            PluginTool(
                name="cloudflare.purgeCache",
                display_name="Purge Cache",
                description="Purge all cache for a zone",
                parameters={"zone_id": {"type": "string"}},
            ),
            PluginTool(
                name="cloudflare.firewallRules",
                display_name="Firewall Rules",
                description="List security/firewall rules",
                parameters={"zone_id": {"type": "string"}},
            ),
        ],
        website_url="https://www.cloudflare.com",
        docs_url="https://developers.cloudflare.com/api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['api_token']}", "Content-Type": "application/json"}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "cloudflare.listZones":
                resp = await client.get("https://api.cloudflare.com/client/v4/zones", headers=self._headers)
            elif tool_name == "cloudflare.dnsRecords":
                resp = await client.get(
                    f"https://api.cloudflare.com/client/v4/zones/{parameters['zone_id']}/dns_records",
                    headers=self._headers,
                    params={"type": parameters.get("type")},
                )
            elif tool_name == "cloudflare.purgeCache":
                resp = await client.post(
                    f"https://api.cloudflare.com/client/v4/zones/{parameters['zone_id']}/purge_cache",
                    headers=self._headers,
                    json={"purge_everything": True},
)
            elif tool_name == "cloudflare.firewallRules":
                resp = await client.get(
                    f"https://api.cloudflare.com/client/v4/zones/{parameters['zone_id']}/firewall/rules",
                    headers=self._headers,
                )
            else:
                raise ValueError(f"Unknown cloudflare tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Cloudflare HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
