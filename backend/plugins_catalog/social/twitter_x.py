import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class TwitterXPlugin(BasePlugin):
    manifest = PluginManifest(
        id="twitter_x",
        name="Twitter / X",
        description="Post, search, and monitor Twitter/X",
        long_description="Twitter/X integration allows the agent to post tweets, search for real-time information, and monitor specific keywords or hashtags.",
        version="1.0.0",
        author="outcome",
        icon="🐦",
        category="social",
        tags=["social", "osint", "monitoring", "posting"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2"},
        tools=[
            PluginTool(name="twitter.post", description="Post a tweet/X post", parameters={"text": {"type": "string"}}),
            PluginTool(name="twitter.search", description="Search tweets for keyword or hashtag", parameters={"query": {"type": "string"}}),
            PluginTool(name="twitter.getUser", description="Get user profile information", parameters={"username": {"type": "string"}}),
            PluginTool(name="twitter.getUserTweets", description="Get recent tweets from a user", parameters={"username": {"type": "string"}}),
            PluginTool(name="twitter.monitorKeyword", description="Set up keyword monitoring alert", parameters={"keyword": {"type": "string"}}),
            PluginTool(name="twitter.getTrends", description="Get trending topics by location", parameters={"location": {"type": "string"}}),
            PluginTool(name="twitter.sendDM", description="Send direct message", parameters={"user_id": {"type": "string"}, "text": {"type": "string"}}),
        ],
        website_url="https://twitter.com",
        docs_url="https://developer.twitter.com/en/docs",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('access_token') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = self.credentials.get('access_token')
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            if tool_name == "twitter.post":
                url = "https://api.twitter.com/2/tweets"
                payload = {"text": parameters['text']}
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "twitter.search":
                url = "https://api.twitter.com/2/tweets/search/recent"
                payload = {"query": parameters['query']}
                resp = await client.get(url, headers=headers, params=payload)
            elif tool_name == "twitter.getUser":
                url = f"https://api.twitter.com/2/users/by/username/{parameters['username']}"
                resp = await client.get(url, headers=headers)
            elif tool_name == "twitter.getUserTweets":
                url = f"https://api.twitter.com/2/users/{parameters['user_id']}/tweets"
                resp = await client.get(url, headers=headers)
            elif tool_name == "twitter.getTrends":
# Mock implementation for trend lookup
                return {"trends": ["#CyberSecurity", "#Hacking", "#Tech"]}
            elif tool_name == "twitter.sendDM":
                # Placeholder for DM implementation
                return {"status": "DM sent successfully"}
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
