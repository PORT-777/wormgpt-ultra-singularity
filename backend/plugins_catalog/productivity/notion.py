import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class NotionPlugin(BasePlugin):
    manifest = PluginManifest(
        id="notion",
        name="Notion",
        description="Create and manage Notion pages and databases",
        long_description="Notion integration allows the agent to automatically log findings, create structured reports, and manage knowledge bases within your Notion workspace.",
        version="1.0.0",
        author="outcome",
        icon="📓",
        category="productivity",
        tags=["notes", "docs", "database", "wiki"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2"},
        tools=[
            PluginTool(name="notion.createPage", description="Create a new page in a database", parameters={"parent_id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}}),
            PluginTool(name="notion.updatePage", description="Update existing page content", parameters={"page_id": {"type": "string"}, "content": {"type": "string"}}),
            PluginTool(name="notion.searchPages", description="Search Notion workspace for pages", parameters={"query": {"type": "string"}}),
            PluginTool(name="notion.createDatabase", description="Create a new database", parameters={"title": {"type": "string"}, "parent_id": {"type": "string"}}),
            PluginTool(name="notion.addDatabaseItem", description="Add a new row to a database", parameters={"database_id": {"type": "string"}, "properties": {"type": "object"}}),
            PluginTool(name="notion.queryDatabase", description="Query a database with filters", parameters={"database_id": {"type": "string"}, "filter": {"type": "object"}}),
            PluginTool(name="notion.saveFinding", description="Quickly save a security finding to Notion", parameters={"title": {"type": "string"}, "severity": {"type": "string"}, "description": {"type": "string"}}),
            PluginTool(name="notion.saveReport", description="Save a full analysis report to a page", parameters={"parent_id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}}),
        ],
        website_url="https://www.notion.so",
        docs_url="https://developers.notion.com/",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('access_token') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = self.credentials.get('access_token')
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if tool_name == "notion.createPage":
                url = "https://api.notion.com/v1/pages"
                payload = {
                    "parent": {"database_id": parameters['parent_id']},
                    "properties": {
                        "title": {
                            "title": [{"text": {"content": parameters['title']}}]
                        }
                    },
                    "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": parameters['content']}}]}}]
                }
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "notion.searchPages":
                url = "https://api.notion.com/v1/search"
                payload = {"query": parameters['query'], "filter": {"property": "object", "value": "page"}}
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "notion.addDatabaseItem":
                url = f"https://api.notion.com/v1/pages"
                payload = {
                    "parent": {"database_id": parameters['database_id']},
                    "properties": parameters['properties']
                }
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "notion.queryDatabase":
                url = f"https://api.notion.com/v1/databases/{parameters['database_id']}/query"
                resp = await client.post(url, headers=headers, json={"filter": parameters['filter']})
            elif tool_name == "notion.saveFinding":
                # Shortcut tool: finds a database named 'Findings' or uses a default
                url = "https://api.notion.com/v1/pages"
                payload = {
                    "parent": {"database_id": "FINDINGS_DB_ID_PLACEHOLDER"}, # Logic would resolve this
                    "properties": {
                        "Name": {"title": [{"text": {"content": parameters['title']}}]},
                        "Severity": {"select": {"name": parameters['severity']}},
                        "Description": {"rich_text": [{"text": {"content": parameters['description']}}]}
                    }
                }
                resp = await client.post(url, headers=headers, json=payload)
            else:
                # Generic implementation for other tools
                raise NotImplementedError(f"Tool {tool_name} not yet fully implemented in this version.")

            resp.raise_for_status()
            return resp.json()
