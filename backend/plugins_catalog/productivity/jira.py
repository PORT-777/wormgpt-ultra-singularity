import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class JiraPlugin(BasePlugin):
    manifest = PluginManifest(
        id="jira",
        name="Jira",
        description="Create and manage Jira issues and projects",
        long_description="Jira integration allows the agent to automate ticket creation, update incident statuses, and track security tasks within your Jira workspace.",
        version="1.0.0",
        author="outcome",
        icon="📋",
        category="productivity",
        tags=["project-management", "tickets", "issues", "tracking"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_token", "domain_field": "domain"},
        tools=[
            PluginTool(name="jira.createIssue", description="Create a new Jira issue/ticket", parameters={"domain": {"type": "string"}, "project_key": {"type": "string"}, "summary": {"type": "string"}, "description": {"type": "string"}, "issue_type": {"type": "string"}}),
            PluginTool(name="jira.updateIssue", description="Update issue status or fields", parameters={"domain": {"type": "string"}, "issue_id": {"type": "string"}, "fields": {"type": "object"}}),
            PluginTool(name="jira.searchIssues", description="Search Jira with JQL query", parameters={"domain": {"type": "string"}, "jql": {"type": "string"}}),
            PluginTool(name="jira.addComment", description="Add comment to an issue", parameters={"domain": {"type": "string"}, "issue_id": {"type": "string"}, "comment": {"type": "string"}}),
            PluginTool(name="jira.getIssue", description="Get issue details", parameters={"domain": {"type": "string"}, "issue_id": {"type": "string"}}),
            PluginTool(name="jira.createIncident", description="Create a security incident ticket", parameters={"domain": {"type": "string"}, "project_key": {"type": "string"}, "summary": {"type": "string"}, "priority": {"type": "string"}}),
        ],
        website_url="https://www.atlassian.com/software/jira",
        docs_url="https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('api_token') is not None and self.credentials.get('domain') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        domain = parameters.get('domain') or self.credentials.get('domain')
        token = self.credentials.get('api_token')
        base_url = f"https://{domain}.atlassian.net/rest/api/3"
        headers = {
            "Authorization": f"Basic {token}", # Note: Jira usually requires Base64(email:token)
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if tool_name == "jira.createIssue" or tool_name == "jira.createIncident":
                url = f"{base_url}/issue"
                payload = {
                    "fields": {
                        "project": {"key": parameters.get('project_key')},
                        "summary": parameters.get('summary'),
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": parameters.get('description', '')}]}]
                        },
                        "issuetype": {"name": parameters.get('issue_type', 'Task') if tool_name == "jira.createIssue" else 'Incident'}
                    }
                }
                # Handle priority if provided
                if 'priority' in parameters:
                    payload['fields']['priority'] = {'name': parameters['priority']}
                
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "jira.updateIssue":
                url = f"{base_url}/issue/{parameters['issue_id']}"
                resp = await client.put(url, headers=headers, json={"fields": parameters['fields']})
            elif tool_name == "jira.searchIssues":
                url = f"{base_url}/search"
                resp = await client.get(url, headers=headers, params={"jql": parameters['jql']})
            elif tool_name == "jira.addComment":
                url = f"{base_url}/issue/{parameters['issue_id']}/comment"
                payload = {
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": parameters['comment']}]}]
                    }
                }
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "jira.getIssue":
                url = f"{base_url}/issue/{parameters['issue_id']}"
                resp = await client.get(url, headers=headers)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
