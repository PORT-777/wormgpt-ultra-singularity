from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://sentry.io/api/0"


@register_plugin
class SentryPlugin(BasePlugin):
    manifest = PluginManifest(
        id="sentry",
        name="Sentry",
        description="Inspect issues, events and resolve errors from projects",
        long_description=(
            "Error monitoring control: list projects, query unresolved issues by "
            "project or search, read stack-trace events, resolve/ignore issues and "
            "track how often an error is still firing."
        ),
        version="1.0.0",
        author="outcome",
        icon="🛡️",
        category="devops",
        tags=["devops", "sentry", "errors", "observability", "monitoring"],
        auth_type="apikey",
        auth_config={"api_key_field": "auth_token", "extra_fields": ["org_slug"]},
        tools=[
            PluginTool(
                name="sentry.listProjects",
                display_name="List Projects",
                description="List projects in the organisation",
                parameters={"org_slug": {"type": "string"}},
            ),
            PluginTool(
                name="sentry.listIssues",
                display_name="List Issues",
                description="List issues for a project with optional search query",
                parameters={
                    "project_slug": {"type": "string"},
                    "query": {"type": "string", "description": "e.g. is:unresolved level:error"},
                    "limit": {"type": "integer", "description": "Default 25"},
                },
            ),
            PluginTool(
                name="sentry.getIssue",
                display_name="Issue Details",
                description="Read an issue's title, culprit, count and first/last seen",
                parameters={"issue_id": {"type": "string"}},
            ),
            PluginTool(
                name="sentry.listEvents",
                display_name="Issue Events",
                description="List the most recent events (stack traces) for an issue",
                parameters={"issue_id": {"type": "string"}},
            ),
            PluginTool(
                name="sentry.resolveIssue",
                display_name="Resolve Issue",
                description="Mark an issue resolved or ignored",
                parameters={
                    "issue_id": {"type": "string"},
                    "status": {"type": "string", "description": "resolved | ignored | unresolved"},
                },
            ),
        ],
        website_url="https://sentry.io",
        docs_url="https://docs.sentry.io/api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("auth_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['auth_token']}"}

    @property
    def _org(self) -> str:
        return self.credentials.get("org_slug", "")

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        org = parameters.get("org_slug") or self._org
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "sentry.listProjects":
                resp = await client.get(
                    f"{BASE}/organizations/{org}/projects/", headers=self._headers
                )
            elif tool_name == "sentry.listIssues":
                resp = await client.get(
                    f"{BASE}/projects/{org}/{parameters['project_slug']}/issues/",
                    headers=self._headers,
                    params={
                        "query": parameters.get("query") or "is:unresolved",
                        "limit": min(int(parameters.get("limit") or 25), 100),
                    },
                )
            elif tool_name == "sentry.getIssue":
                resp = await client.get(
                    f"{BASE}/issues/{parameters['issue_id']}/", headers=self._headers
                )
            elif tool_name == "sentry.listEvents":
                resp = await client.get(
                    f"{BASE}/issues/{parameters['issue_id']}/events/",
                    headers=self._headers,
                    params={"full": "true"},
                )
            elif tool_name == "sentry.resolveIssue":
                resp = await client.put(
                    f"{BASE}/issues/{parameters['issue_id']}/",
                    headers=self._headers,
                    json={"status": parameters.get("status") or "resolved"},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Sentry HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
