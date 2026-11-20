from typing import Any, Dict

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

API = "https://api.clickup.com/api/v2"


@register_plugin
class ClickUpPlugin(BasePlugin):
    manifest = PluginManifest(
        id="clickup",
        name="ClickUp",
        description="Manage ClickUp spaces, lists and tasks",
        long_description=(
            "ClickUp API v2 with an OAuth access token: list teams, spaces and "
            "tasks, create tasks, read a task and change its status."
        ),
        version="1.0.0",
        author="outcome",
        icon="✅",
        category="productivity",
        tags=["productivity", "clickup", "tasks", "projects", "pm"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="clickup.listTeams",
                description="List authorized teams/workspaces",
                parameters={},
            ),
            PluginTool(
                name="clickup.listSpaces",
                description="List spaces in a team",
                parameters={"team_id": {"type": "string"}},
            ),
            PluginTool(
                name="clickup.listTasks",
                description="List tasks in a list",
                parameters={"list_id": {"type": "string"}},
            ),
            PluginTool(
                name="clickup.getTask",
                description="Get a task by id",
                parameters={"task_id": {"type": "string"}},
            ),
            PluginTool(
                name="clickup.createTask",
                description="Create a task in a list",
                parameters={
                    "list_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
            ),
            PluginTool(
                name="clickup.updateTask",
                description="Update a task's status",
                parameters={
                    "task_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            ),
        ],
        website_url="https://clickup.com",
        docs_url="https://clickup.com/api",
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
            if tool_name == "clickup.listTeams":
                resp = await client.get(f"{API}/team", headers=headers)
            elif tool_name == "clickup.listSpaces":
                resp = await client.get(
                    f"{API}/team/{parameters['team_id']}/space", headers=headers
                )
            elif tool_name == "clickup.listTasks":
                resp = await client.get(
                    f"{API}/list/{parameters['list_id']}/task", headers=headers
                )
            elif tool_name == "clickup.getTask":
                resp = await client.get(
                    f"{API}/task/{parameters['task_id']}", headers=headers
                )
            elif tool_name == "clickup.createTask":
                resp = await client.post(
                    f"{API}/list/{parameters['list_id']}/task",
                    headers=headers,
                    json={
                        "name": parameters["name"],
                        "description": parameters.get("description") or "",
                    },
                )
            elif tool_name == "clickup.updateTask":
                resp = await client.put(
                    f"{API}/task/{parameters['task_id']}",
                    headers=headers,
                    json={"status": parameters["status"]},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "ok"}
