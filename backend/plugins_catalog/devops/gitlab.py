import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class GitLabPlugin(BasePlugin):
    manifest = PluginManifest(
        id="gitlab",
        name="GitLab",
        description="GitLab repository and CI/CD management",
        long_description="GitLab integration allows the agent to manage repositories, create issues, trigger pipelines, and search code via the GitLab API.",
        version="1.0.0",
        author="outcome",
        icon="🦊",
        category="devops",
        tags=["code", "ci-cd", "repository", "devops"],
        auth_type="apikey",
        auth_config={"api_key_field": "private_token"},
        tools=[
            PluginTool(name="gitlab.createIssue", description="Create a new GitLab issue", parameters={"project_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}}),
            PluginTool(name="gitlab.triggerPipeline", description="Trigger a CI/CD pipeline", parameters={"project_id": {"type": "string"}, "ref": {"type": "string"}}),
            PluginTool(name="gitlab.getMergeRequests", description="List open merge requests", parameters={"project_id": {"type": "string"}, "state": {"type": "string"}}),
            PluginTool(name="gitlab.searchCode", description="Search code in GitLab", parameters={"search": {"type": "string"}, "scope": {"type": "string", "description": "projects, groups, or users"}}),
        ],
        website_url="https://about.gitlab.com",
        docs_url="https://docs.gitlab.com/ee/api/",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('private_token') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = self.credentials.get('private_token')
        headers = {"PRIVATE-TOKEN": token}
        
        async with httpx.AsyncClient() as client:
            if tool_name == "gitlab.createIssue":
                url = f"https://gitlab.com/api/v4/projects/{parameters['project_id']}/issues"
                payload = {
                    "title": parameters['title'],
                    "description": parameters.get('description', '')
                }
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "gitlab.triggerPipeline":
                url = f"https://gitlab.com/api/v4/projects/{parameters['project_id']}/pipeline"
                payload = {"ref": parameters['ref']}
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "gitlab.getMergeRequests":
                url = f"https://gitlab.com/api/v4/projects/{parameters['project_id']}/merge_requests"
                params = {"state": parameters.get("state", "opened")}
                resp = await client.get(url, headers=headers, params=params)
            elif tool_name == "gitlab.searchCode":
                url = "https://gitlab.com/api/v4/search"
                params = {
                    "scope": parameters.get("scope", "projects"),
"search": parameters['search']
                }
                resp = await client.get(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
