from typing import Any, Dict, List

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

API = "https://api.spotify.com/v1"


@register_plugin
class SpotifyPlugin(BasePlugin):
    manifest = PluginManifest(
        id="spotify",
        name="Spotify",
        description="Search music, manage playlists and inspect your profile",
        long_description=(
            "Spotify Web API with an OAuth access token: search tracks and artists, "
            "read track metadata, list and create playlists, and add tracks to a "
            "playlist."
        ),
        version="1.0.0",
        author="outcome",
        icon="🎧",
        category="social",
        tags=["social", "music", "spotify", "playlists", "media"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="spotify.search",
                description="Search Spotify catalogue",
                parameters={
                    "q": {"type": "string"},
                    "type": {"type": "string", "description": "track|artist|album|playlist"},
                    "limit": {"type": "integer"},
                },
            ),
            PluginTool(
                name="spotify.getTrack",
                description="Get a track by id",
                parameters={"track_id": {"type": "string"}},
            ),
            PluginTool(
                name="spotify.listPlaylists",
                description="List the current user's playlists",
                parameters={"limit": {"type": "integer"}},
            ),
            PluginTool(
                name="spotify.createPlaylist",
                description="Create a playlist for the current user",
                parameters={
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "public": {"type": "boolean"},
                },
            ),
            PluginTool(
                name="spotify.addTracks",
                description="Add tracks (URIs) to a playlist",
                parameters={
                    "playlist_id": {"type": "string"},
                    "uris": {"type": "array", "items": {"type": "string"}},
                },
            ),
            PluginTool(
                name="spotify.getProfile",
                description="Return the linked Spotify profile",
                parameters={},
            ),
        ],
        website_url="https://www.spotify.com",
        docs_url="https://developer.spotify.com/documentation/web-api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['access_token']}"}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "spotify.search":
                resp = await client.get(
                    f"{API}/search",
                    headers=headers,
                    params={
                        "q": parameters["q"],
                        "type": parameters.get("type") or "track",
                        "limit": min(int(parameters.get("limit") or 10), 50),
                    },
                )
            elif tool_name == "spotify.getTrack":
                resp = await client.get(
                    f"{API}/tracks/{parameters['track_id']}", headers=headers
                )
            elif tool_name == "spotify.listPlaylists":
                resp = await client.get(
                    f"{API}/me/playlists",
                    headers=headers,
                    params={"limit": min(int(parameters.get("limit") or 20), 50)},
                )
            elif tool_name == "spotify.createPlaylist":
                me = await client.get(f"{API}/me", headers=headers)
                me.raise_for_status()
                user_id = (me.json() or {}).get("id")
                if not user_id:
                    raise RuntimeError("Could not resolve the Spotify user id")
                resp = await client.post(
                    f"{API}/users/{user_id}/playlists",
                    headers=headers,
                    json={
                        "name": parameters["name"],
                        "description": parameters.get("description") or "",
                        "public": bool(parameters.get("public")),
                    },
                )
            elif tool_name == "spotify.addTracks":
                uris: List[str] = [str(u) for u in (parameters.get("uris") or [])]
                if not uris:
                    raise ValueError("uris is required")
                resp = await client.post(
                    f"{API}/playlists/{parameters['playlist_id']}/tracks",
                    headers=headers,
                    json={"uris": uris},
                )
            elif tool_name == "spotify.getProfile":
                resp = await client.get(f"{API}/me", headers=headers)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json() if resp.content else {"status": "ok"}
