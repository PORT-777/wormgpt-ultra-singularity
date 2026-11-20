from typing import Any, Dict

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

API = "https://app.asana.com/api/1.0"


@register_plugin
class AsanaPlugin(BasePlugin):
    manifest = PluginManifest(
        id="asana",
        name="Asana",
        description="Manage Asana projects, tasks and workspaces",
        long_description=(
            "Asana API with an OAuth access token: list workspaces, projects and "
            "tasks, create tasks, fetch a task and mark tasks complete."
        ),
        version="1.0.0",
        author="outcome",
        icon="🔺",
        category="productivity",
        tags=["productivity", "asana", "tasks", "projects", "pm"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="asana.listWorkspaces",
                description="List workspaces",
                parameters={},
            ),
            PluginTool(
                name="asana.listProjects",
                description="List projects in a workspace",
                parameters={"workspace": {"type": "string"}},
            ),
            PluginTool(
                name="asana.listTasks",
                description="List tasks in a project",
                parameters={"project": {"type": "string"}},
            ),
            PluginTool(
                name="asana.getTask",
                description="Get a task by id",
                parameters={"task_id": {"type": "string"}},
            ),
            PluginTool(
                name="asana.createTask",
                description="Create a task in a project",
                parameters={
                    "name": {"type": "string"},
                    "project": {"type": "string"},
                    "notes": {"type": "string"},
                    "assignee": {"type": "string"},
                },
            ),
            PluginTool(
                name="asana.completeTask",
                description="Mark a task complete",
                parameters={"task_id": {"type": "string"}},
            ),
        ],
        website_url="https://asana.com",
        docs_url="https://developers.asana.com/docs",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "asana.listWorkspaces":
                resp = await client.get(f"{API}/workspaces", headers=headers)
            elif tool_name == "asana.listProjects":
                resp = await client.get(
                    f"{API}/projects",
                    headers=headers,
                    params={"workspace": parameters["workspace"], "limit": 100},
                )
            elif tool_name == "asana.listTasks":
                resp = await client.get(
                    f"{API}/tasks",
                    headers=headers,
                    params={"project": parameters["project"], "limit": 100},
                )
            elif tool_name == "asana.getTask":
                resp = await client.get(
                    f"{API}/tasks/{parameters['task_id']}", headers=headers
                )
            elif tool_name == "asana.createTask":
                data: Dict[str, Any] = {
                    "name": parameters["name"],
                    "projects": [parameters["project"]],
                }
                if parameters.get("notes"):
                    data["notes"] = parameters["notes"]
                if parameters.get("assignee"):
                    data["assignee"] = parameters["assignee"]
                resp = await client.post(
                    f"{API}/tasks", headers=headers, json={"data": data}
                )
            elif tool_name == "asana.completeTask":
                resp = await client.put(
                    f"{API}/tasks/{parameters['task_id']}",
                    headers=headers,
                    json={"data": {"completed": True}},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "ok"}
