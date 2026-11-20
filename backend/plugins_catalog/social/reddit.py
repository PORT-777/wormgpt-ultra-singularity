from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class RedditPlugin(BasePlugin):
    manifest = PluginManifest(
        id="reddit",
        name="Reddit",
        description="Search, post, and monitor Reddit communities",
        long_description="Reddit integration lets the agent search posts and comments, pull subreddit metadata, and monitor keywords for OSINT or threat discussion tracking.",
        version="1.0.0",
        author="outcome",
        icon="👽",
        category="social",
        tags=["social", "osint", "monitoring", "research"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="reddit.search",
                display_name="Search Reddit",
                description="Search Reddit posts and comments",
                parameters={"q": {"type": "string"}, "subreddit": {"type": "string"}},
            ),
            PluginTool(
                name="reddit.getSubreddit",
                display_name="Get Subreddit",
                description="Get subreddit info and top posts",
                parameters={"subreddit": {"type": "string"}, "sort": {"type": "string"}},
            ),
            PluginTool(
                name="reddit.submitPost",
                display_name="Submit Post",
                description="Submit a post to a subreddit",
                parameters={"subreddit": {"type": "string"}, "title": {"type": "string"}, "text": {"type": "string"}},
            ),
            PluginTool(
                name="reddit.monitorKeyword",
                display_name="Monitor Keyword",
                description="Search recent posts mentioning a keyword",
                parameters={"keyword": {"type": "string"}, "limit": {"type": "integer"}},
            ),
            PluginTool(
                name="reddit.getUser",
                display_name="Get User",
                description="Get a Reddit user profile",
                parameters={"username": {"type": "string"}},
            ),
        ],
        website_url="https://www.reddit.com",
        docs_url="https://www.reddit.com/dev/api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"bearer {self.credentials['access_token']}",
            "User-Agent": "CybersecAgent/1.0",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if tool_name == "reddit.search":
                sub = parameters.get("subreddit")
                path = f"/r/{sub}/search" if sub else "/search"
                resp = await client.get(
                    f"https://oauth.reddit.com{path}",
                    headers=self._headers,
                    params={"q": parameters["q"], "restrict_sr": bool(sub), "limit": 25},
                )
            elif tool_name == "reddit.getSubreddit":
                resp = await client.get(
                    f"https://oauth.reddit.com/r/{parameters['subreddit']}/{parameters.get('sort', 'hot')}",
                    headers=self._headers,
                    params={"limit": 25},
                )
            elif tool_name == "reddit.submitPost":
                resp = await client.post(
                    "https://oauth.reddit.com/api/submit",
                    headers=self._headers,
                    data={
                        "sr": parameters["subreddit"],
                        "title": parameters["title"],
                        "text": parameters.get("text", ""),
                        "kind": "self",
                    },
                )
            elif tool_name == "reddit.monitorKeyword":
                resp = await client.get(
                    "https://oauth.reddit.com/search",
                    headers=self._headers,
                    params={
                        "q": parameters["keyword"],
                        "sort": "new",
                        "limit": parameters.get("limit", 50),
                    },
                )
            elif tool_name == "reddit.getUser":
                resp = await client.get(
                    f"https://oauth.reddit.com/user/{parameters['username']}/about",
                    headers=self._headers,
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
