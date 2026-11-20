from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://services.nvd.nist.gov/rest/json"


@register_plugin
class NVDPlugin(BasePlugin):
    manifest = PluginManifest(
        id="nvd",
        name="NIST NVD",
        description="Search CVEs, CVSS scores and CPE matches from the NVD",
        long_description=(
            "Official NIST National Vulnerability Database feed: keyword, CVE id, "
            "CPE and CVSS severity searches, plus the newest published and modified "
            "vulnerabilities. No key required; an optional API key raises the rate limit."
        ),
        version="1.0.0",
        author="outcome",
        icon="🏛️",
        category="security",
        tags=["security", "nvd", "cve", "cvss", "vulnerability"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="nvd.searchCves",
                display_name="Search CVEs",
                description="Keyword search across CVE descriptions",
                parameters={
                    "keyword": {"type": "string"},
                    "results_per_page": {"type": "integer", "description": "Default 20, max 2000"},
                },
            ),
            PluginTool(
                name="nvd.getCve",
                display_name="Get CVE",
                description="Fetch one CVE with CVSS metrics and references",
                parameters={"cve_id": {"type": "string", "description": "e.g. CVE-2024-3094"}},
            ),
            PluginTool(
                name="nvd.bySeverity",
                display_name="By Severity",
                description="List CVEs for a CVSS v3 severity level",
                parameters={
                    "severity": {"type": "string", "description": "CRITICAL | HIGH | MEDIUM | LOW"},
                    "results_per_page": {"type": "integer"},
                },
            ),
            PluginTool(
                name="nvd.recent",
                display_name="Recently Published",
                description="CVEs published in the last N days",
                parameters={
                    "days": {"type": "integer", "description": "Default 7, max 120"},
                    "results_per_page": {"type": "integer"},
                },
            ),
        ],
        website_url="https://nvd.nist.gov",
        docs_url="https://nvd.nist.gov/developers/vulnerabilities",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        # Public endpoint: credentials are optional, only a rate-limit key.
        return True

    @property
    def _headers(self) -> Dict[str, str]:
        key = self.credentials.get("api_key")
        return {"apiKey": key} if key else {}

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.get(f"{BASE}{path}", headers=self._headers, params=params)
            if resp.status_code >= 400:
                raise RuntimeError(f"NVD HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()

    @staticmethod
    def _summarize(data: Dict[str, Any]) -> Dict[str, Any]:
        out = []
        for item in data.get("vulnerabilities", []):
            cve = item.get("cve", {})
            metrics = cve.get("metrics", {})
            score = None
            severity = None
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                entries = metrics.get(key) or []
                if entries:
                    primary = entries[0].get("cvssData", {})
                    score = primary.get("baseScore")
                    severity = primary.get("baseSeverity") or entries[0].get("baseSeverity")
                    break
            descriptions = cve.get("descriptions") or []
            summary = next(
                (d.get("value") for d in descriptions if d.get("lang") == "en"),
                descriptions[0].get("value") if descriptions else "",
            )
            out.append(
                {
                    "id": cve.get("id"),
                    "published": cve.get("published"),
                    "last_modified": cve.get("lastModified"),
                    "status": cve.get("vulnStatus"),
                    "score": score,
                    "severity": severity,
                    "description": summary,
                }
            )
        return {
            "total_results": data.get("totalResults", 0),
            "vulnerabilities": out,
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        per_page = min(int(parameters.get("results_per_page") or 20), 2000)

        if tool_name == "nvd.searchCves":
            data = await self._get(
                "/cves/2.0",
                {"keywordSearch": parameters.get("keyword", ""), "resultsPerPage": per_page},
            )
            return self._summarize(data)

        if tool_name == "nvd.getCve":
            data = await self._get("/cves/2.0", {"cveId": parameters["cve_id"]})
            summary = self._summarize(data)
            if summary["vulnerabilities"]:
                summary["vulnerabilities"][0]["references"] = [
                    r.get("url")
                    for r in (
                        ((data.get("vulnerabilities") or [{}])[0].get("cve") or {}).get(
                            "references", []
                        )
                    )
                ]
            return summary

        if tool_name == "nvd.bySeverity":
            data = await self._get(
                "/cves/2.0",
                {
                    "cvssV3Severity": (parameters.get("severity") or "CRITICAL").upper(),
                    "resultsPerPage": per_page,
                },
            )
            return self._summarize(data)

        if tool_name == "nvd.recent":
            from datetime import datetime, timedelta, timezone

            days = min(int(parameters.get("days") or 7), 120)
            start = datetime.now(timezone.utc) - timedelta(days=days)
            data = await self._get(
                "/cves/2.0",
                {
                    "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "pubEndDate": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z"
                    ),
                    "resultsPerPage": per_page,
                },
            )
            return self._summarize(data)

        raise ValueError(f"Unknown tool: {tool_name}")
