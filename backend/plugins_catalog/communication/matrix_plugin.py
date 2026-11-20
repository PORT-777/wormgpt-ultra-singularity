from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class MatrixPlugin(BasePlugin):
    manifest = PluginManifest(
        id="matrix",
        name="Matrix",
        description="Send messages and manage rooms on any Matrix homeserver",
        long_description=(
            "Client-Server API client: send text, notice and markdown messages, create "
            "and join rooms, list joined rooms and resolve room aliases. Works with "
            "Synapse, Dendrite and Element-hosted homeservers."
        ),
        version="1.0.0",
        author="outcome",
        icon="🔷",
        category="communication",
        tags=["communication", "matrix", "chat", "federated", "rooms"],
        auth_type="apikey",
        auth_config={"api_key_field": "access_token", "extra_fields": ["homeserver"]},
        tools=[
            PluginTool(
                name="matrix.sendMessage",
                display_name="Send Message",
                description="Send a message to a room id or alias",
                parameters={
                    "room": {"type": "string", "description": "!room:server or #alias:server"},
                    "message": {"type": "string"},
                    "format": {"type": "string", "description": "text | markdown | notice"},
                },
            ),
            PluginTool(
                name="matrix.createRoom",
                display_name="Create Room",
                description="Create a room with a name, topic and optional invites",
                parameters={
                    "name": {"type": "string"},
                    "topic": {"type": "string"},
                    "invite": {"type": "array", "description": "Matrix user ids"},
                    "preset": {"type": "string", "description": "private_chat | public_chat"},
                },
            ),
            PluginTool(
                name="matrix.joinRoom",
                display_name="Join Room",
                description="Join a room by id or alias",
                parameters={"room": {"type": "string"}},
            ),
            PluginTool(
                name="matrix.listRooms",
                display_name="List Rooms",
                description="List joined rooms with names and member counts",
                parameters={},
            ),
        ],
        website_url="https://matrix.org",
        docs_url="https://spec.matrix.org/latest/client-server-api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _base(self) -> str:
        raw = (self.credentials.get("homeserver") or "https://matrix.org").rstrip("/")
        if not raw.startswith("http"):
            raw = "https://" + raw
        return raw + "/_matrix/client/v3"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    async def _resolve(self, client: httpx.AsyncClient, room: str) -> str:
        if room.startswith("#"):
            resp = await client.get(
                f"{self._base}/directory/room/{room}", headers=self._headers
            )
            resp.raise_for_status()
            return resp.json().get("room_id", room)
        return room

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        import asyncio
        import time
        import uuid

        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "matrix.sendMessage":
                room_id = await self._resolve(client, parameters["room"])
                fmt = parameters.get("format") or "text"
                body = parameters.get("message", "")
                content: Dict[str, Any] = {"msgtype": "m.notice" if fmt == "notice" else "m.text", "body": body}
                if fmt == "markdown":
                    content["format"] = "org.matrix.custom.html"
                    content["formatted_body"] = body
                txn = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
                resp = await client.put(
                    f"{self._base}/rooms/{room_id}/send/m.room.message/{txn}",
                    headers=self._headers,
                    json=content,
                )
            elif tool_name == "matrix.createRoom":
                payload: Dict[str, Any] = {
                    "name": parameters.get("name", ""),
                    "preset": parameters.get("preset") or "private_chat",
                }
                if parameters.get("topic"):
                    payload["topic"] = parameters["topic"]
                if parameters.get("invite"):
                    payload["invite"] = parameters["invite"]
                resp = await client.post(
                    f"{self._base}/createRoom", headers=self._headers, json=payload
                )
            elif tool_name == "matrix.joinRoom":
                room_id = await self._resolve(client, parameters["room"])
                resp = await client.post(
                    f"{self._base}/join/{room_id}", headers=self._headers, json={}
                )
            elif tool_name == "matrix.listRooms":
                resp = await client.get(
                    f"{self._base}/joined_rooms", headers=self._headers
                )
            else:
                raise ValueError(f"Unknown matrix tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Matrix HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
