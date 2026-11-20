from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.twitch.tv/helix"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"


@register_plugin
class TwitchPlugin(BasePlugin):
    manifest = PluginManifest(
        id="twitch",
        name="Twitch",
        description="Live streams, top games, channel data and clips",
        long_description=(
            "Twitch Helix API: find who is live right now, list the most watched games, "
            "pull channel metadata and follower counts, and surface recent clips. "
            "Supports either a user access token or client-credentials flow."
        ),
        version="1.0.0",
        author="outcome",
        icon="🎮",
        category="social",
        tags=["social", "twitch", "streaming", "gaming", "live"],
        auth_type="apikey",
        auth_config={
            "api_key_field": "access_token",
            "extra_fields": ["client_id", "client_secret"],
        },
        tools=[
            PluginTool(
                name="twitch.getUser",
                display_name="Get User",
                description="Resolve a login name to a user id, description and avatar",
                parameters={"login": {"type": "string"}},
            ),
            PluginTool(
                name="twitch.liveStreams",
                display_name="Live Streams",
                description="List currently live streams, optionally filtered by game or language",
                parameters={
                    "game_id": {"type": "string"},
                    "language": {"type": "string", "description": "ISO 639-1, e.g. en"},
                    "first": {"type": "integer", "description": "Default 20, max 100"},
                },
            ),
            PluginTool(
                name="twitch.topGames",
                display_name="Top Games",
                description="List the most popular games on Twitch right now",
                parameters={"first": {"type": "integer"}},
            ),
            PluginTool(
                name="twitch.channelInfo",
                display_name="Channel Info",
                description="Get title, game, follower count and live status for a broadcaster",
                parameters={"broadcaster_id": {"type": "string"}},
            ),
            PluginTool(
                name="twitch.clips",
                display_name="Clips",
                description="List recent clips for a broadcaster with view counts",
                parameters={
                    "broadcaster_id": {"type": "string"},
                    "first": {"type": "integer"},
                },
            ),
        ],
        website_url="https://www.twitch.tv",
        docs_url="https://dev.twitch.tv/docs/api/reference",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        has_app = bool(self.credentials.get("client_id")) and bool(
            self.credentials.get("client_secret")
        )
        return bool(self.credentials.get("access_token")) or has_app

    async def _resolve_token(self) -> str:
        if self.credentials.get("access_token"):
            return self.credentials["access_token"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                TOKEN_URL,
                params={
                    "client_id": self.credentials["client_id"],
                    "client_secret": self.credentials["client_secret"],
                    "grant_type": "client_credentials",
                },
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Twitch token HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()["access_token"]

    async def _headers(self) -> Dict[str, str]:
        return {
            "Client-Id": self.credentials.get("client_id", ""),
            "Authorization": f"Bearer {await self._resolve_token()}",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "twitch.getUser":
                resp = await client.get(
                    f"{BASE}/users", headers=headers, params={"login": parameters["login"]}
                )
            elif tool_name == "twitch.liveStreams":
                params: Dict[str, Any] = {
                    "first": min(int(parameters.get("first") or 20), 100)
                }
                if parameters.get("game_id"):
                    params["game_id"] = parameters["game_id"]
                if parameters.get("language"):
                    params["language"] = parameters["language"]
                resp = await client.get(f"{BASE}/streams", headers=headers, params=params)
            elif tool_name == "twitch.topGames":
                resp = await client.get(
                    f"{BASE}/games/top",
                    headers=headers,
                    params={"first": min(int(parameters.get("first") or 20), 100)},
                )
            elif tool_name == "twitch.channelInfo":
                resp = await client.get(
                    f"{BASE}/channels",
                    headers=headers,
                    params={"broadcaster_id": parameters["broadcaster_id"]},
                )
            elif tool_name == "twitch.clips":
                resp = await client.get(
                    f"{BASE}/clips",
                    headers=headers,
                    params={
                        "broadcaster_id": parameters["broadcaster_id"],
                        "first": min(int(parameters.get("first") or 20), 100),
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Twitch HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
