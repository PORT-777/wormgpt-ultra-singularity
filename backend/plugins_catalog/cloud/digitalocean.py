from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.digitalocean.com/v2"


@register_plugin
class DigitalOceanPlugin(BasePlugin):
    manifest = PluginManifest(
        id="digitalocean",
        name="DigitalOcean",
        description="Droplets, snapshots, domains and account balance",
        long_description=(
            "Manage DigitalOcean infrastructure: list and reboot droplets, take "
            "snapshots, power droplets on/off, list domains and DNS records, and read "
            "account limits and billing balance."
        ),
        version="1.0.0",
        author="outcome",
        icon="🌊",
        category="cloud",
        tags=["cloud", "digitalocean", "vps", "droplets", "infrastructure"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_token"},
        tools=[
            PluginTool(
                name="digitalocean.listDroplets",
                display_name="List Droplets",
                description="List droplets with status, region, size and IPs",
                parameters={"tag_name": {"type": "string"}},
            ),
            PluginTool(
                name="digitalocean.getDroplet",
                display_name="Droplet Details",
                description="Get a droplet's configuration, IPs and disk usage",
                parameters={"droplet_id": {"type": "string"}},
            ),
            PluginTool(
                name="digitalocean.powerAction",
                display_name="Power Action",
                description="Power on, off, reboot, shutdown or snapshot a droplet",
                parameters={
                    "droplet_id": {"type": "string"},
                    "action": {
                        "type": "string",
                        "description": "power_on | power_off | reboot | shutdown | snapshot",
                    },
                    "snapshot_name": {"type": "string"},
                },
            ),
            PluginTool(
                name="digitalocean.listDomains",
                display_name="List Domains",
                description="List domains managed by the account",
                parameters={},
            ),
            PluginTool(
                name="digitalocean.listDnsRecords",
                display_name="DNS Records",
                description="List DNS records under a domain",
                parameters={"domain": {"type": "string"}},
            ),
            PluginTool(
                name="digitalocean.account",
                display_name="Account",
                description="Read account status, droplet limit and balance",
                parameters={},
            ),
        ],
        website_url="https://www.digitalocean.com",
        docs_url="https://docs.digitalocean.com/reference/api/",
        is_free=False,
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
            if tool_name == "digitalocean.listDroplets":
                resp = await client.get(
                    f"{BASE}/droplets",
                    headers=self._headers,
                    params={
                        "per_page": 100,
                        **(
                            {"tag_name": parameters["tag_name"]}
                            if parameters.get("tag_name")
                            else {}
                        ),
                    },
                )
            elif tool_name == "digitalocean.getDroplet":
                resp = await client.get(
                    f"{BASE}/droplets/{parameters['droplet_id']}", headers=self._headers
                )
            elif tool_name == "digitalocean.powerAction":
                body: Dict[str, Any] = {"type": parameters["action"]}
                if parameters["action"] == "snapshot":
                    body["name"] = parameters.get("snapshot_name") or "agent-snapshot"
                resp = await client.post(
                    f"{BASE}/droplets/{parameters['droplet_id']}/actions",
                    headers=self._headers,
                    json=body,
                )
            elif tool_name == "digitalocean.listDomains":
                resp = await client.get(f"{BASE}/domains", headers=self._headers)
            elif tool_name == "digitalocean.listDnsRecords":
                resp = await client.get(
                    f"{BASE}/domains/{parameters['domain']}/records",
                    headers=self._headers,
                    params={"per_page": 200},
                )
            elif tool_name == "digitalocean.account":
                account = await client.get(f"{BASE}/account", headers=self._headers)
                balance = await client.get(f"{BASE}/customers/my/balance", headers=self._headers)
                if account.status_code >= 400:
                    raise RuntimeError(
                        f"DigitalOcean HTTP {account.status_code}: {account.text[:400]}"
                    )
                return {
                    "account": account.json().get("account", {}),
                    "balance": balance.json() if balance.status_code < 400 else {},
                }
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"DigitalOcean HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
