import asyncio
from typing import Any, Dict, List, Optional
import json
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import PLUGIN_REGISTRY, get_plugin_from_registry

@register_plugin
class SlackPlugin(BasePlugin):
    manifest = PluginManifest(
        id="slack",
        name="Slack",
        description="Send messages and alerts to Slack channels",
        long_description="Slack integration allows the agent to post updates, security alerts, and full reports to Slack channels via Webhooks or Bot Tokens.",
        version="1.0.0",
        author="outcome",
        icon="🖖",
        category="communication",
        tags=["team", "alerts", "notifications", "messaging"],
        auth_type="webhook",
        auth_config={"webhook_url_field": "webhook_url"},
        tools=[
            PluginTool(name="slack.sendMessage", description="Send a text message to a channel", parameters={"text": {"type": "string"}}),
            PluginTool(name="slack.sendAlert", description="Send a formatted security alert", parameters={"text": {"type": "string"}, "color": {"type": "string"}}),
            PluginTool(name="slack.sendReport", description="Share a report as a Slack message", parameters={"text": {"type": "string"}}),
            PluginTool(name="slack.uploadFile", description="Upload a file to Slack", parameters={"file_url": {"type": "string"}, "initial_comment": {"type": "string"}}),
        ],
        website_url="https://slack.com",
        docs_url="https://api.slack.com/methods/chat.postMessage",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('webhook_url') is not None and self.credentials.get('webhook_url').startswith("https://hooks.slack.com/")

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        webhook_url = self.credentials.get('webhook_url')
        
        async with httpx.AsyncClient() as client:
            if tool_name == "slack.sendMessage":
                payload = {"text": parameters['text']}
                resp = await client.post(webhook_url, json=payload)
            elif tool_name == "slack.sendAlert":
                color = parameters.get("color", "#FF0000")
                payload = {
                    "attachments": [{
                        "color": color,
                        "text": parameters['text'],
                        "fallback": "Security Alert"
                    }]
                }
                resp = await client.post(webhook_url, json=payload)
            elif tool_name == "slack.sendReport":
                payload = {"text": f"*Security Report:*\n{parameters['text']}"}
                resp = await client.post(webhook_url, json=payload)
            elif tool_name == "slack.uploadFile":
                # Slack webhooks for files usually require the files.upload API (not just incoming webhooks)
                # This is a placeholder implementation for when using a Bot Token instead of a Webhook
                raise NotImplementedError("File upload via simple webhooks is limited. Please use Bot Token authentication for file uploads.")
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return {"status": "sent"}
