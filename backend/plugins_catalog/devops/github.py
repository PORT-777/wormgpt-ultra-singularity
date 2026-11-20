import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class GitHubPlugin(BasePlugin):
    manifest = PluginManifest(
        id="github",
        name="GitHub",
        description="Manage repositories, issues, and pull requests",
        long_description="GitHub integration allows the agent to create issues, search code, and manage repositories using a Personal Access Token (PAT).",
        version="1.0.0",
        author="outcome",
        icon="🐙",
        category="devops",
        tags=["code", "repository", "issues", "git"],
        auth_type="apikey",
        auth_config={"api_key_field": "token"},
        tools=[
            PluginTool(name="github.createIssue", description="Create a new issue in a repository", parameters={"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}}),
            PluginTool(name="github.searchCode", description="Search for code across GitHub", parameters={"q": {"type": "string"}}),
            PluginTool(name="github.getRepository", description="Get repository information", parameters={"owner": {"type": "string"}, "repo": {"type": "string"}}),
            PluginTool(name="github.createPR", description="Create a pull request", parameters={"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "head": {"type": "string"}, "base": {"type": "string"}}),
        ],
        website_url="https://github.com",
        docs_url="https://docs.github.com/en/rest",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('token') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = self.credentials.get('token')
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            if tool_name == "github.createIssue":
                url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/issues"
                payload = {"title": parameters['title'], "body": parameters.get('body', '')}
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "github.searchCode":
                url = "https://api.github.com/search/code"
                payload = {"q": parameters['q']}
                resp = await client.get(url, headers=headers, params=payload)
            elif tool_name == "github.getRepository":
                url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}"
                resp = await client.get(url, headers=headers)
            elif tool_name == "github.createPR":
                url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/pulls"
                payload = {
                    "title": parameters['title'],
                    "head": parameters['head'],
"base": parameters['base']
                }
                resp = await client.post(url, headers=headers, json=payload)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
