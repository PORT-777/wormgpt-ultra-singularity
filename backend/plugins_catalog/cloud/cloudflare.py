from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.cloudflare.com/client/v4"


@register_plugin
class CloudflarePlugin(BasePlugin):
    manifest = PluginManifest(
        id="cloudflare",
        name="Cloudflare",
        description="Zones, DNS records, cache purge and firewall rules",
        long_description=(
            "Manage Cloudflare from the agent: list zones, read and create DNS "
            "records, purge the edge cache for URLs or everything, and review "
            "firewall/security rules per zone."
        ),
        version="1.0.0",
        author="outcome",
        icon="🌩️",
        category="cloud",
        tags=["cloud", "cloudflare", "dns", "cdn", "waf"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_token"},
        tools=[
            PluginTool(
                name="cloudflare.listZones",
                display_name="List Zones",
                description="List zones with status, plan and name servers",
                parameters={"name": {"type": "string", "description": "Filter by domain"}},
            ),
            PluginTool(
                name="cloudflare.listDnsRecords",
                display_name="List DNS Records",
                description="List DNS records for a zone, optionally filtered by type",
                parameters={
                    "zone_id": {"type": "string"},
                    "type": {"type": "string", "description": "A | AAAA | CNAME | TXT ..."},
                },
            ),
            PluginTool(
                name="cloudflare.createDnsRecord",
                display_name="Create DNS Record",
                description="Create an A/AAAA/CNAME/TXT/MX record with optional proxying",
                parameters={
                    "zone_id": {"type": "string"},
                    "type": {"type": "string"},
                    "name": {"type": "string"},
                    "content": {"type": "string"},
                    "ttl": {"type": "integer", "description": "1 = automatic"},
                    "proxied": {"type": "boolean"},
                },
            ),
            PluginTool(
                name="cloudflare.purgeCache",
                display_name="Purge Cache",
                description="Purge specific URLs or the entire zone cache",
                parameters={
                    "zone_id": {"type": "string"},
                    "urls": {"type": "array", "description": "Empty = purge everything"},
                },
            ),
            PluginTool(
                name="cloudflare.listFirewallRules",
                display_name="Firewall Rules",
                description="List legacy firewall rules for a zone",
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
        return {
            "Authorization": f"Bearer {self.credentials['api_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "cloudflare.listZones":
                resp = await client.get(
                    f"{BASE}/zones",
                    headers=self._headers,
                    params={
                        "per_page": 50,
                        **({"name": parameters["name"]} if parameters.get("name") else {}),
                    },
                )
            elif tool_name == "cloudflare.listDnsRecords":
                resp = await client.get(
                    f"{BASE}/zones/{parameters['zone_id']}/dns_records",
                    headers=self._headers,
                    params={
                        "per_page": 100,
                        **({"type": parameters["type"]} if parameters.get("type") else {}),
                    },
                )
            elif tool_name == "cloudflare.createDnsRecord":
                resp = await client.post(
                    f"{BASE}/zones/{parameters['zone_id']}/dns_records",
                    headers=self._headers,
                    json={
                        "type": parameters["type"],
                        "name": parameters["name"],
                        "content": parameters["content"],
                        "ttl": int(parameters.get("ttl") or 1),
                        "proxied": bool(parameters.get("proxied")),
                    },
                )
            elif tool_name == "cloudflare.purgeCache":
                urls = parameters.get("urls") or []
                resp = await client.post(
                    f"{BASE}/zones/{parameters['zone_id']}/purge_cache",
                    headers=self._headers,
                    json={"files": urls} if urls else {"purge_everything": True},
                )
            elif tool_name == "cloudflare.listFirewallRules":
                resp = await client.get(
                    f"{BASE}/zones/{parameters['zone_id']}/firewall/rules",
                    headers=self._headers,
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Cloudflare HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()
            if data.get("success") is False:
                raise RuntimeError(f"Cloudflare error: {data.get('errors')}")
            return data
