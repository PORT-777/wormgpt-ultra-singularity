from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

FEED = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)


@register_plugin
class CisaKevPlugin(BasePlugin):
    manifest = PluginManifest(
        id="cisa_kev",
        name="CISA KEV",
        description="CISA Known Exploited Vulnerabilities catalog search",
        long_description=(
            "The authoritative list of vulnerabilities exploited in the wild. Search "
            "by vendor, product, CVE or ransomware use, and see the required "
            "remediation due dates. No authentication required."
        ),
        version="1.0.0",
        author="outcome",
        icon="🇺🇸",
        category="security",
        tags=["security", "cisa", "kev", "exploited", "remediation"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="cisa_kev.list",
                display_name="List All",
                description="Return catalog metadata plus the newest entries",
                parameters={"limit": {"type": "integer", "description": "Default 50"}},
            ),
            PluginTool(
                name="cisa_kev.search",
                display_name="Search",
                description="Search vendor, product, CVE id or short description",
                parameters={
                    "query": {"type": "string"},
                    "ransomware_only": {"type": "boolean"},
                    "limit": {"type": "integer"},
                },
            ),
            PluginTool(
                name="cisa_kev.stats",
                display_name="Statistics",
                description="Count entries by vendor and by ransomware use",
                parameters={"top": {"type": "integer", "description": "Default 10 vendors"}},
            ),
        ],
        website_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        docs_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def _catalog(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
            resp = await client.get(FEED)
            if resp.status_code >= 400:
                raise RuntimeError(f"CISA HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        data = await self._catalog()
        vulns = data.get("vulnerabilities", [])

        if tool_name == "cisa_kev.list":
            limit = int(parameters.get("limit") or 50)
            return {
                "catalog_version": data.get("catalogVersion"),
                "date_released": data.get("dateReleased"),
                "count": data.get("count"),
                "vulnerabilities": vulns[-limit:],
            }

        if tool_name == "cisa_kev.search":
            q = (parameters.get("query") or "").lower()
            only_ransom = bool(parameters.get("ransomware_only"))
            matches = [
                v
                for v in vulns
                if (not q or q in str(v).lower())
                and (not only_ransom or v.get("knownRansomwareCampaignUse") == "Known")
            ]
            return {
                "count": len(matches),
                "vulnerabilities": matches[: int(parameters.get("limit") or 50)],
            }

        if tool_name == "cisa_kev.stats":
            top = int(parameters.get("top") or 10)
            vendors: Dict[str, int] = {}
            ransomware = 0
            for v in vulns:
                vendors[v.get("vendorProject", "?")] = vendors.get(v.get("vendorProject", "?"), 0) + 1
                if v.get("knownRansomwareCampaignUse") == "Known":
                    ransomware += 1
            ranked = sorted(vendors.items(), key=lambda kv: kv[1], reverse=True)[:top]
            return {
                "total": len(vulns),
                "ransomware_related": ransomware,
                "top_vendors": [{"vendor": k, "count": v} for k, v in ranked],
            }

        raise ValueError(f"Unknown tool: {tool_name}")
