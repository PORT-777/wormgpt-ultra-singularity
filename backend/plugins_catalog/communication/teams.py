"""Microsoft Teams plugin — Graph API + incoming webhooks."""
from __future__ import annotations

import base64
import binascii
import json
from typing import Any, Dict

import httpx

from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

GRAPH = "https://graph.microsoft.com"


@register_plugin
class TeamsPlugin(BasePlugin):
    manifest = PluginManifest(
        id="teams",
        name="Microsoft Teams",
        description="Send messages and manage Teams through Graph or webhooks",
        long_description="Post to channels via incoming webhook or use a Microsoft Graph token to list teams/channels, create meetings and upload files.",
        version="2.0.0",
        author="PORT 777",
        icon="teams",
        category="communication",
        tags=["team", "alerts", "microsoft", "enterprise"],
        auth_type="oauth2",
        auth_config={"webhook_url_field": "webhook_url", "access_token_field": "access_token"},
        tools=[
            PluginTool(name="teams.sendMessage", description="Send a message via incoming webhook",
                       parameters={"text": {"type": "string"}}),
            PluginTool(name="teams.sendAdaptiveCard", description="Send an adaptive card",
                       parameters={"card": {"type": "object"}}),
            PluginTool(name="teams.sendAlert", description="Send a formatted alert",
                       parameters={"title": {"type": "string"}, "summary": {"type": "string"}}),
            PluginTool(name="teams.listTeams", description="List joined teams via Graph",
                       parameters={}),
            PluginTool(name="teams.listChannels", description="List channels of a team",
                       parameters={"team_id": {"type": "string"}}),
            PluginTool(name="teams.createMeeting", description="Create an online meeting",
                       parameters={"subject": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}}),
            PluginTool(name="teams.uploadFile", description="Upload a file to a channel Files tab",
                       parameters={"team_id": {"type": "string"}, "channel_id": {"type": "string"},
                                   "filename": {"type": "string"}, "content_b64": {"type": "string"}}),
        ],
        website_url="https://www.microsoft.com/microsoft-teams",
        docs_url="https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/graph-api-teams",
        is_free=True,
        is_official=True,
    )

    def __init__(self, credentials: Dict[str, Any] | None = None):
        super().__init__(credentials or {})
        if not self.credentials.get("webhook_url") and not self.credentials.get("access_token"):
            raise ValueError("webhook_url or access_token is required")

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("webhook_url") or self.credentials.get("access_token"))

    def _graph_headers(self) -> Dict[str, str]:
        token = self.credentials.get("access_token")
        if not token:
            raise ValueError("Microsoft Graph token is required for this tool")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _webhook(self) -> str:
        url = self.credentials.get("webhook_url")
        if not url:
            raise ValueError("incoming webhook URL is required for this tool")
        return str(url)

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        params = parameters or {}
        async with httpx.AsyncClient(timeout=30) as client:
            if tool_name in {"teams.sendMessage", "teams.sendAdaptiveCard", "teams.sendAlert"}:
                url = self._webhook()
                if tool_name == "teams.sendAdaptiveCard":
                    payload = params.get("card") or {}
                elif tool_name == "teams.sendAlert":
                    payload = {
                        "@type": "MessageCard",
                        "title": str(params.get("title", "")),
                        "text": str(params.get("summary", "")),
                    }
                else:
                    payload = {"text": str(params.get("text", ""))}
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return {"status": "sent"}

            if tool_name == "teams.listTeams":
                resp = await client.get(f"{GRAPH}/v1.0/me/joinedTeams", headers=self._graph_headers())
                resp.raise_for_status()
                return {"teams": (resp.json() or {}).get("value") or []}

            if tool_name == "teams.listChannels":
                team_id = str(params.get("team_id", ""))
                resp = await client.get(f"{GRAPH}/v1.0/teams/{team_id}/channels", headers=self._graph_headers())
                resp.raise_for_status()
                return {"channels": (resp.json() or {}).get("value") or []}

            if tool_name == "teams.createMeeting":
                attendees = []
                for attendee in params.get("attendees") or []:
                    email = attendee if isinstance(attendee, str) else (attendee.get("email") or attendee.get("address") or "")
                    attendees.append({"identity": {"user": {"id": email}}})
                payload = {
                    "subject": str(params.get("subject", "")),
                    "startDateTime": str(params.get("start", "")),
                    "endDateTime": str(params.get("end", "")),
                    "participants": {"attendees": attendees},
                }
                resp = await client.post(f"{GRAPH}/v1.0/me/onlineMeetings", headers=self._graph_headers(), json=payload)
                resp.raise_for_status()
                data = resp.json() or {}
                return {"join_url": data.get("joinWebUrl", ""), "meeting": data}

            if tool_name == "teams.uploadFile":
                encoded = str(params.get("content_b64", ""))
                try:
                    content = base64.b64decode(encoded, validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise ValueError("content_b64 is not valid base64") from exc
                team_id = str(params.get("team_id", ""))
                channel_id = str(params.get("channel_id", ""))
                filename = str(params.get("filename", "file.bin"))
                folder = await client.get(
                    f"{GRAPH}/v1.0/teams/{team_id}/channels/{channel_id}/filesFolder",
                    headers=self._graph_headers(),
                )
                folder.raise_for_status()
                info = folder.json() or {}
                drive_id = (info.get("parentReference") or {}).get("driveId") or info.get("driveId")
                item_id = info.get("id")
                if not drive_id or not item_id:
                    raise ValueError("Graph did not return a channel files folder")
                url = f"{GRAPH}/v1.0/drives/{drive_id}/items/{item_id}:/{filename}:/content"
                resp = await client.put(url, headers=self._graph_headers(), content=content)
                resp.raise_for_status()
                data = resp.json() or {}
                return {"status": "uploaded", "web_url": data.get("webUrl", ""), "file": data}

            raise ValueError(f"Unknown tool: {tool_name}")
