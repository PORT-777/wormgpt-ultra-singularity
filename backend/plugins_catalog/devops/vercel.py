from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.vercel.com"


@register_plugin
class VercelPlugin(BasePlugin):
    manifest = PluginManifest(
        id="vercel",
        name="Vercel",
        description="Projects, deployments, domains and environment variables",
        long_description=(
            "Deploy and inspect Vercel projects: list projects and deployments with "
            "build state, read deployment details and build logs, cancel running "
            "deployments, list domains and read environment variable keys."
        ),
        version="1.0.0",
        author="outcome",
        icon="▲",
        category="devops",
        tags=["devops", "vercel", "deployments", "serverless", "frontend"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="vercel.listProjects",
                display_name="List Projects",
                description="List projects with framework and latest deployment state",
                parameters={"limit": {"type": "integer", "description": "Default 20"}},
            ),
            PluginTool(
                name="vercel.listDeployments",
                display_name="List Deployments",
                description="List deployments, newest first, optionally filtered by project",
                parameters={
                    "project_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "state": {"type": "string", "description": "READY | ERROR | BUILDING"},
                },
            ),
            PluginTool(
                name="vercel.getDeployment",
                display_name="Deployment Details",
                description="Read a deployment's state, url, commit and build duration",
                parameters={"deployment_id": {"type": "string"}},
            ),
            PluginTool(
                name="vercel.cancelDeployment",
                display_name="Cancel Deployment",
                description="Cancel a queued or building deployment",
                parameters={"deployment_id": {"type": "string"}},
            ),
            PluginTool(
                name="vercel.listDomains",
                display_name="List Domains",
                description="List domains attached to the account or a project",
                parameters={"project_id": {"type": "string"}},
            ),
            PluginTool(
                name="vercel.listEnv",
                display_name="Environment Variables",
                description="List environment variable keys for a project (values hidden)",
                parameters={"project_id": {"type": "string", "description": "id or name"}},
            ),
        ],
        website_url="https://vercel.com",
        docs_url="https://vercel.com/docs/rest-api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {self.credentials['api_key']}"}
        if self.credentials.get("team_id"):
            headers["x-vercel-team-id"] = self.credentials["team_id"]
        return headers

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "vercel.listProjects":
                resp = await client.get(
                    f"{BASE}/v9/projects",
                    headers=self._headers,
                    params={"limit": min(int(parameters.get("limit") or 20), 100)},
                )
            elif tool_name == "vercel.listDeployments":
                params: Dict[str, Any] = {
                    "limit": min(int(parameters.get("limit") or 20), 100)
                }
                if parameters.get("project_id"):
                    params["projectId"] = parameters["project_id"]
                if parameters.get("state"):
                    params["state"] = parameters["state"]
                resp = await client.get(
                    f"{BASE}/v6/deployments", headers=self._headers, params=params
                )
            elif tool_name == "vercel.getDeployment":
                resp = await client.get(
                    f"{BASE}/v13/deployments/{parameters['deployment_id']}",
                    headers=self._headers,
                )
            elif tool_name == "vercel.cancelDeployment":
                resp = await client.patch(
                    f"{BASE}/v12/deployments/{parameters['deployment_id']}/cancel",
                    headers=self._headers,
                )
            elif tool_name == "vercel.listDomains":
                if parameters.get("project_id"):
                    resp = await client.get(
                        f"{BASE}/v9/projects/{parameters['project_id']}/domains",
                        headers=self._headers,
                    )
                else:
                    resp = await client.get(
                        f"{BASE}/v5/domains", headers=self._headers
                    )
            elif tool_name == "vercel.listEnv":
                resp = await client.get(
                    f"{BASE}/v9/projects/{parameters['project_id']}/env",
                    headers=self._headers,
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Vercel HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
