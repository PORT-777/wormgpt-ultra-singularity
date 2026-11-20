from typing import Any, Dict

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

API = "https://api.zoom.us/v2"


@register_plugin
class ZoomPlugin(BasePlugin):
    manifest = PluginManifest(
        id="zoom",
        name="Zoom",
        description="Schedule meetings and inspect recordings",
        long_description=(
            "Zoom API v2 with an OAuth access token: list, create and read "
            "meetings, list cloud recordings and inspect the linked user."
        ),
        version="1.0.0",
        author="outcome",
        icon="🎥",
        category="communication",
        tags=["communication", "zoom", "meetings", "video", "recordings"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="zoom.listMeetings",
                description="List meetings for a user",
                parameters={
                    "user_id": {"type": "string", "description": "'me' or a user id"},
                    "type": {"type": "string", "description": "scheduled|upcoming|live"},
                },
            ),
            PluginTool(
                name="zoom.getMeeting",
                description="Get a meeting by id",
                parameters={"meeting_id": {"type": "string"}},
            ),
            PluginTool(
                name="zoom.createMeeting",
                description="Schedule a meeting",
                parameters={
                    "topic": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO-8601 UTC"},
                    "duration": {"type": "integer", "description": "minutes"},
                    "timezone": {"type": "string"},
                },
            ),
            PluginTool(
                name="zoom.listRecordings",
                description="List cloud recordings for a user",
                parameters={"user_id": {"type": "string"}},
            ),
            PluginTool(
                name="zoom.getUser",
                description="Return the linked Zoom user",
                parameters={},
            ),
        ],
        website_url="https://zoom.us",
        docs_url="https://developers.zoom.us/docs/api/",
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
        user = parameters.get("user_id") or "me"
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "zoom.listMeetings":
                resp = await client.get(
                    f"{API}/users/{user}/meetings",
                    headers=headers,
                    params={"type": parameters.get("type") or "scheduled"},
                )
            elif tool_name == "zoom.getMeeting":
                resp = await client.get(
                    f"{API}/meetings/{parameters['meeting_id']}", headers=headers
                )
            elif tool_name == "zoom.createMeeting":
                resp = await client.post(
                    f"{API}/users/me/meetings",
                    headers=headers,
                    json={
                        "topic": parameters["topic"],
                        "type": 2,
                        "start_time": parameters.get("start_time") or "",
                        "duration": int(parameters.get("duration") or 30),
                        "timezone": parameters.get("timezone") or "UTC",
                    },
                )
            elif tool_name == "zoom.listRecordings":
                resp = await client.get(
                    f"{API}/users/{user}/recordings", headers=headers
                )
            elif tool_name == "zoom.getUser":
                resp = await client.get(f"{API}/users/me", headers=headers)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "ok"}
