from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://www.googleapis.com/youtube/v3"


@register_plugin
class YouTubePlugin(BasePlugin):
    manifest = PluginManifest(
        id="youtube",
        name="YouTube",
        description="Search videos, read channel stats, comments and video details",
        long_description=(
            "Wraps the YouTube Data API v3: search the whole catalogue, pull video "
            "statistics (views, likes, comments), inspect a channel's growth, read "
            "comment threads and list a playlist's contents."
        ),
        version="1.0.0",
        author="outcome",
        icon="▶️",
        category="social",
        tags=["social", "video", "youtube", "search", "analytics"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="youtube.search",
                display_name="Search Videos",
                description="Search YouTube for videos, channels or playlists",
                parameters={
                    "query": {"type": "string"},
                    "type": {"type": "string", "description": "video | channel | playlist"},
                    "max_results": {"type": "integer", "description": "Default 10, max 50"},
                    "order": {"type": "string", "description": "relevance | date | viewCount | rating"},
                },
            ),
            PluginTool(
                name="youtube.videoDetails",
                display_name="Video Details",
                description="Get title, duration, views, likes and description for video ids",
                parameters={"video_ids": {"type": "array", "description": "Up to 50 ids"}},
            ),
            PluginTool(
                name="youtube.channelStats",
                display_name="Channel Stats",
                description="Get subscriber, view and video counts for a channel id or handle",
                parameters={
                    "channel_id": {"type": "string"},
                    "handle": {"type": "string", "description": "e.g. @MrBeast"},
                },
            ),
            PluginTool(
                name="youtube.comments",
                display_name="Comment Threads",
                description="Read top-level comments for a video",
                parameters={
                    "video_id": {"type": "string"},
                    "max_results": {"type": "integer"},
                    "order": {"type": "string", "description": "relevance | time"},
                },
            ),
            PluginTool(
                name="youtube.playlistItems",
                display_name="Playlist Items",
                description="List the videos inside a playlist",
                parameters={
                    "playlist_id": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
            ),
        ],
        website_url="https://www.youtube.com",
        docs_url="https://developers.google.com/youtube/v3/docs",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _key(self) -> str:
        return self.credentials["api_key"]

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.get(f"{BASE}{path}", params={**params, "key": self._key})
            if resp.status_code >= 400:
                raise RuntimeError(f"YouTube HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "youtube.search":
            data = await self._get(
                "/search",
                {
                    "part": "snippet",
                    "q": parameters.get("query", ""),
                    "type": parameters.get("type") or "video",
                    "maxResults": min(int(parameters.get("max_results") or 10), 50),
                    "order": parameters.get("order") or "relevance",
                },
            )
            return {
                "results": [
                    {
                        "id": (item.get("id") or {}).get(
                            "videoId"
                        ) or (item.get("id") or {}).get("channelId")
                        or (item.get("id") or {}).get("playlistId"),
                        "title": (item.get("snippet") or {}).get("title"),
                        "channel": (item.get("snippet") or {}).get("channelTitle"),
                        "published": (item.get("snippet") or {}).get("publishedAt"),
                        "description": (item.get("snippet") or {}).get("description"),
                    }
                    for item in data.get("items", [])
                ]
            }

        if tool_name == "youtube.videoDetails":
            ids = parameters.get("video_ids") or []
            data = await self._get(
                "/videos",
                {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[:50])},
            )
            return {
                "videos": [
                    {
                        "id": item.get("id"),
                        "title": (item.get("snippet") or {}).get("title"),
                        "channel": (item.get("snippet") or {}).get("channelTitle"),
                        "published": (item.get("snippet") or {}).get("publishedAt"),
                        "duration": (item.get("contentDetails") or {}).get("duration"),
                        "views": (item.get("statistics") or {}).get("viewCount"),
                        "likes": (item.get("statistics") or {}).get("likeCount"),
                        "comments": (item.get("statistics") or {}).get("commentCount"),
                    }
                    for item in data.get("items", [])
                ]
            }

        if tool_name == "youtube.channelStats":
            params: Dict[str, Any] = {"part": "snippet,statistics"}
            if parameters.get("channel_id"):
                params["id"] = parameters["channel_id"]
            elif parameters.get("handle"):
                params["forHandle"] = parameters["handle"]
            else:
                raise ValueError("channel_id or handle is required")
            data = await self._get("/channels", params)
            return {
                "channels": [
                    {
                        "id": item.get("id"),
                        "title": (item.get("snippet") or {}).get("title"),
                        "country": (item.get("snippet") or {}).get("country"),
                        "subscribers": (item.get("statistics") or {}).get("subscriberCount"),
                        "views": (item.get("statistics") or {}).get("viewCount"),
                        "videos": (item.get("statistics") or {}).get("videoCount"),
                    }
                    for item in data.get("items", [])
                ]
            }

        if tool_name == "youtube.comments":
            data = await self._get(
                "/commentThreads",
                {
                    "part": "snippet",
                    "videoId": parameters["video_id"],
                    "maxResults": min(int(parameters.get("max_results") or 20), 100),
                    "order": parameters.get("order") or "relevance",
                    "textFormat": "plainText",
                },
            )
            return {
                "comments": [
                    {
                        "author": (
                            ((item.get("snippet") or {}).get("topLevelComment") or {}).get(
                                "snippet"
                            )
                            or {}
                        ).get("authorDisplayName"),
                        "text": (
                            ((item.get("snippet") or {}).get("topLevelComment") or {}).get(
                                "snippet"
                            )
                            or {}
                        ).get("textDisplay"),
                        "likes": (
                            ((item.get("snippet") or {}).get("topLevelComment") or {}).get(
                                "snippet"
                            )
                            or {}
                        ).get("likeCount"),
                    }
                    for item in data.get("items", [])
                ]
            }

        if tool_name == "youtube.playlistItems":
            data = await self._get(
                "/playlistItems",
                {
                    "part": "snippet,contentDetails",
                    "playlistId": parameters["playlist_id"],
                    "maxResults": min(int(parameters.get("max_results") or 25), 50),
                },
            )
            return {
                "items": [
                    {
                        "video_id": (item.get("contentDetails") or {}).get("videoId"),
                        "title": (item.get("snippet") or {}).get("title"),
                        "position": (item.get("snippet") or {}).get("position"),
                    }
                    for item in data.get("items", [])
                ]
            }

        raise ValueError(f"Unknown tool: {tool_name}")
