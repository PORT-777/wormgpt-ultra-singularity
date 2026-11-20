from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class DigitalOceanPlugin(BasePlugin):
    manifest = PluginManifest(
        id="digitalocean",
        name="DigitalOcean",
        description="Manage Droplets, Volumes, and Networking",
        long_description=(
            "Control DigitalOcean infrastructure: list and manage droplets, "
            "inspect volumes, manage floating IPs, and monitor account usage."
        ),
        version="1.0.0",
        author="outcome",
        icon="🌊",
        category="cloud",
        tags=["cloud", "digitalocean", "droplets", "vps", "infrastructure"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_token"},
        tools=[
            PluginTool(
                name="digitalocean.listDroplets",
                display_name="List Droplets",
                description="Get a list of all droplets in the account",
                parameters={},
            ),
            PluginTool(
                name="digitalocean.getDroplet",
                display_name="Droplet Details",
                description="Get full details for a specific droplet",
                parameters={"droplet_id": {"type": "string"}},
            ),
            PluginTool(
                name="digitalocean.powerAction",
                display_name="Power Action",
                description="Perform an action (on, off, reboot) on a droplet",
                parameters={
                    "droplet_id": {"type": "string"},
                    "action": {"type": "string", "description": "on | off | reboot"},
                },
            ),
            PluginTool(
                name="digitalocean.listVolumes",
                display_name="List Volumes",
                description="List all block storage volumes",
                parameters={},
            ),
            PluginTool(
                name="digitalocean.listIPs",
                display_name="List IPs",
                description="List all IP addresses (Floating/Reserved) in the account",
                parameters={},
            ),
        ],
        website_url="https://www.digitalocean.com",
        docs_url="https://docs.digitalocean.com/reference/api/api-endpoints/",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['api_token']}", "Content-Type": "application/json"}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "digitalocean.listDroplets":
                resp = await client.get("https://api.digitalocean.com/v2/droplets", headers=self._headers)
            elif tool_name == "digitalocean.getDroplet":
                resp = await client.get(f"https://api.digitalocean.com/v2/droplets/{parameters['droplet_id']}", headers=self._headers)
            elif tool_name == "digitalocean.powerAction":
                resp = await client.post(
                    f"https://api.digitalocean.com/v2/droplets/{parameters['droplet_id']}/actions",
                    headers=self._headers,
                    json={"type": parameters["action"]}
                )
            elif tool_name == "digitalocean.listVolumes":
                resp = await client.get("https://api.digitalocean.com/v2/volumes", headers=self._headers)
            elif tool_name == "digitalocean.listIPs":
                resp = await client.get("https://api.digitalocean.com/v2/floating_ips", headers=self._headers)
            else:
                raise ValueError(f"Unknown digitalocean tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"DigitalOcean HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
