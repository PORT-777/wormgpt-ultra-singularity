from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class MISPPlugin(BasePlugin):
    manifest = PluginManifest(
        id="misp",
        name="MISP",
        description="Malware Information Sharing Platform",
        long_description="MISP is an open-source threat intelligence platform. Query IOCs across events, create new events, and export STIX bundles for sharing.",
        version="1.0.0",
        author="outcome",
        icon="🕸️",
        category="security",
        tags=["threat-intel", "ioc-sharing", "malware"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "url_field": "misp_url"},
        tools=[
            PluginTool(
                name="misp.searchIOC",
                display_name="Search IOC",
                description="Search for an indicator across all MISP events",
                parameters={"value": {"type": "string", "description": "IOC value: hash, IP, domain, URL"}},
            ),
            PluginTool(
                name="misp.createEvent",
                display_name="Create Event",
                description="Create a new MISP threat event",
                parameters={
                    "info": {"type": "string", "description": "Event title/info"},
                    "distribution": {"type": "integer"},
                    "threat_level_id": {"type": "integer"},
                },
            ),
            PluginTool(
                name="misp.addAttribute",
                display_name="Add Attribute",
                description="Add an IOC attribute to an existing MISP event",
                parameters={
                    "event_id": {"type": "string"},
                    "type": {"type": "string", "description": "e.g. sha256, ip-dst, domain"},
                    "value": {"type": "string"},
                    "category": {"type": "string"},
                },
            ),
            PluginTool(
                name="misp.getEvent",
                display_name="Get Event",
                description="Get full details of a MISP event by ID",
                parameters={"event_id": {"type": "string"}},
            ),
            PluginTool(
                name="misp.exportSTIX",
                display_name="Export STIX",
                description="Export an event as a STIX 2.1 bundle for sharing",
                parameters={"event_id": {"type": "string"}},
            ),
        ],
        website_url="https://www.misp-project.org",
        docs_url="https://www.misp-project.org/openapi/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key")) and bool(self.credentials.get("misp_url"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.credentials["api_key"],
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @property
    def _base(self) -> str:
        return self.credentials["misp_url"].rstrip("/")

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            if tool_name == "misp.searchIOC":
                resp = await client.post(
                    f"{self._base}/attributes/restSearch",
                    headers=self._headers,
                    json={"value": parameters["value"]},
                )
            elif tool_name == "misp.createEvent":
                payload = {
                    "Event": {
                        "info": parameters["info"],
                        "distribution": parameters.get("distribution", 0),
                        "threat_level_id": parameters.get("threat_level_id", 2),
                        "analysis": 0,
                    }
                }
                resp = await client.post(
                    f"{self._base}/events/add", headers=self._headers, json=payload
                )
            elif tool_name == "misp.addAttribute":
                payload = {
                    "Attribute": {
                        "event_id": parameters["event_id"],
                        "type": parameters["type"],
                        "value": parameters["value"],
                        "category": parameters.get("category", "Other"),
                    }
                }
                resp = await client.post(
                    f"{self._base}/attributes/add", headers=self._headers, json=payload
                )
            elif tool_name == "misp.getEvent":
                resp = await client.get(
                    f"{self._base}/events/view/{parameters['event_id']}", headers=self._headers
                )
            elif tool_name == "misp.exportSTIX":
                resp = await client.get(
                    f"{self._base}/events/restSearch",
                    headers=self._headers,
                    params={"returnFormat": "stix2", "eventid": parameters["event_id"]},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            return resp.json() if "json" in ct else {"raw": resp.text}
