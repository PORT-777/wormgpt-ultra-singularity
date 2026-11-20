from typing import Any, Dict

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.hubapi.com"


@register_plugin
class HubSpotPlugin(BasePlugin):
    manifest = PluginManifest(
        id="hubspot",
        name="HubSpot",
        description="Read and create CRM contacts and deals",
        long_description=(
            "HubSpot CRM API v3 with an OAuth access token: list and search "
            "contacts and deals, fetch records by id, and create new contacts "
            "and deals."
        ),
        version="1.0.0",
        author="outcome",
        icon="🧲",
        category="marketing",
        tags=["marketing", "crm", "hubspot", "contacts", "deals"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="hubspot.listContacts",
                description="List CRM contacts",
                parameters={"limit": {"type": "integer"}},
            ),
            PluginTool(
                name="hubspot.getContact",
                description="Get a contact by id",
                parameters={"contact_id": {"type": "string"}},
            ),
            PluginTool(
                name="hubspot.createContact",
                description="Create a contact",
                parameters={
                    "email": {"type": "string"},
                    "firstname": {"type": "string"},
                    "lastname": {"type": "string"},
                },
            ),
            PluginTool(
                name="hubspot.listDeals",
                description="List CRM deals",
                parameters={"limit": {"type": "integer"}},
            ),
            PluginTool(
                name="hubspot.createDeal",
                description="Create a deal",
                parameters={
                    "dealname": {"type": "string"},
                    "amount": {"type": "string"},
                    "dealstage": {"type": "string"},
                },
            ),
            PluginTool(
                name="hubspot.search",
                description="Search CRM objects by text",
                parameters={
                    "object_type": {"type": "string", "description": "contacts|deals|companies"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            ),
        ],
        website_url="https://www.hubspot.com",
        docs_url="https://developers.hubspot.com/docs/api/crm/understanding-the-crm",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "hubspot.listContacts":
                resp = await client.get(
                    f"{BASE}/crm/v3/objects/contacts",
                    headers=headers,
                    params={"limit": min(int(parameters.get("limit") or 20), 100)},
                )
            elif tool_name == "hubspot.getContact":
                resp = await client.get(
                    f"{BASE}/crm/v3/objects/contacts/{parameters['contact_id']}",
                    headers=headers,
                )
            elif tool_name == "hubspot.createContact":
                props = {
                    k: parameters[k]
                    for k in ("email", "firstname", "lastname")
                    if parameters.get(k)
                }
                resp = await client.post(
                    f"{BASE}/crm/v3/objects/contacts",
                    headers=headers,
                    json={"properties": props},
                )
            elif tool_name == "hubspot.listDeals":
                resp = await client.get(
                    f"{BASE}/crm/v3/objects/deals",
                    headers=headers,
                    params={"limit": min(int(parameters.get("limit") or 20), 100)},
                )
            elif tool_name == "hubspot.createDeal":
                props = {
                    k: parameters[k]
                    for k in ("dealname", "amount", "dealstage")
                    if parameters.get(k)
                }
                resp = await client.post(
                    f"{BASE}/crm/v3/objects/deals",
                    headers=headers,
                    json={"properties": props},
                )
            elif tool_name == "hubspot.search":
                obj = str(parameters.get("object_type") or "contacts")
                resp = await client.post(
                    f"{BASE}/crm/v3/objects/{obj}/search",
                    headers=headers,
                    json={
                        "query": parameters.get("query") or "",
                        "limit": min(int(parameters.get("limit") or 10), 100),
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "ok"}
