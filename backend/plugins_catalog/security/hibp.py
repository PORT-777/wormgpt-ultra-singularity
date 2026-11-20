from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://haveibeenpwned.com/api/v3"


@register_plugin
class HibpPlugin(BasePlugin):
    manifest = PluginManifest(
        id="hibp",
        name="Have I Been Pwned",
        description="Breach exposure, pastes and domain-wide breach checks",
        long_description=(
            "Check whether an email appears in known data breaches, list every breach "
            "for an account with data classes, inspect pastes, and audit all breached "
            "accounts on a verified domain."
        ),
        version="1.0.0",
        author="outcome",
        icon="🔓",
        category="security",
        tags=["security", "hibp", "breach", "credentials", "osint"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="hibp.breaches",
                display_name="All Breaches",
                description="List every breach in the database (optionally by domain)",
                parameters={"domain": {"type": "string"}},
            ),
            PluginTool(
                name="hibp.accountBreaches",
                display_name="Account Breaches",
                description="List breaches that include a specific email address",
                parameters={
                    "email": {"type": "string"},
                    "truncate": {"type": "boolean", "description": "Hide breach names"},
                },
            ),
            PluginTool(
                name="hibp.accountPastes",
                display_name="Account Pastes",
                description="List pastes that mention an email address",
                parameters={"email": {"type": "string"}},
            ),
            PluginTool(
                name="hibp.breachedDomain",
                display_name="Breached Domain",
                description="List breached account names on a verified domain",
                parameters={"domain": {"type": "string"}},
            ),
        ],
        website_url="https://haveibeenpwned.com",
        docs_url="https://haveibeenpwned.com/API/v3",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "hibp-api-key": self.credentials["api_key"],
            "User-Agent": "OutcomePlugin/1.0",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "hibp.breaches":
                params = {"domain": parameters["domain"]} if parameters.get("domain") else {}
                resp = await client.get(f"{BASE}/breaches", headers=self._headers, params=params)
            elif tool_name == "hibp.accountBreaches":
                resp = await client.get(
                    f"{BASE}/breachedaccount/{parameters['email']}",
                    headers=self._headers,
                    params={
                        "truncateResponse": str(bool(parameters.get("truncate"))).lower()
                    },
                )
            elif tool_name == "hibp.accountPastes":
                resp = await client.get(
                    f"{BASE}/pasteaccount/{parameters['email']}", headers=self._headers
                )
            elif tool_name == "hibp.breachedDomain":
                resp = await client.get(
                    f"{BASE}/breacheddomain/{parameters['domain']}", headers=self._headers
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code == 404:
                return {"count": 0, "results": []}
            if resp.status_code == 429:
                raise RuntimeError("HIBP rate limit reached — wait and retry")
            if resp.status_code >= 400:
                raise RuntimeError(f"HIBP HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()
            if isinstance(data, list):
                return {"count": len(data), "results": data}
            return data
