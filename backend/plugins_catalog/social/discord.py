from typing import Dict, Any
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin
import httpx

@register_plugin
class DiscordPlugin(BasePlugin):
    manifest = PluginManifest(
        id="discord",
        name="Discord",
        description="Send messages, alerts, and reports to Discord",
        long_description="Discord integration allows the agent to send formatted alerts, messages, and files to specific channels using webhooks or bot tokens.",
        version="1.0.0",
        author="outcome",
        icon="💬",
        category="social",
        tags=["social", "alerts", "team", "notifications"],
        auth_type="webhook",
        auth_config={"webhook_url_field": "webhook_url"},
        tools=[
            PluginTool(name="discord.sendMessage", description="Send a simple text message", parameters={"content": {"type": "string"}}),
            PluginTool(name="discord.sendEmbed", description="Send a rich embed message", parameters={"embed": {"type": "object"}}),
            PluginTool(name="discord.sendAlert", description="Send a formatted security alert", parameters={"alert_text": {"type": "string"}, "color": {"type": "integer"}}),
            PluginTool(name="discord.sendFile", description="Upload and share a report file", parameters={"file_url": {"type": "string"}, "content": {"type": "string"}}),
        ],
        website_url="https://discord.com",
        docs_url="https://discord.com/developers/docs/resources/channel#message-create",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('webhook_url') is not None and self.credentials.get('webhook_url').startswith("https://discord.com/api/webhooks/")

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        webhook_url = self.credentials.get('webhook_url')
        
        async with httpx.AsyncClient() as client:
            if tool_name == "discord.sendMessage":
                payload = {"content": parameters['content']}
                resp = await client.post(webhook_url, json=payload)
            elif tool_name == "discord.sendEmbed":
                payload = {"embeds": [parameters['embed']]}
                resp = await client.post(webhook_url, json=payload)
            elif tool_name == "discord.sendAlert":
                color = parameters.get("color", 0xFF0000) # Default Red
                payload = {
                    "embeds": [{
                        "title": "🚨 Security Alert",
                        "description": parameters['alert_text'],
                        "color": color
                    }]
                }
                resp = await client.post(webhook_url, json=payload)
            elif tool_name == "discord.sendFile":
                # Webhooks can receive files via multipart/form-data
                # This is a simplified implementation for a URL-based file
                import httpx
                file_resp = await client.get(parameters['file_url'])
                files = {'file': ('report.txt', file_resp.content)}
                data = {'content': parameters.get('content', '')}
                resp = await client.post(webhook_url, data=data, files=files)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return {"status": "sent"}
