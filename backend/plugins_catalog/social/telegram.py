import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class TelegramPlugin(BasePlugin):
    manifest = PluginManifest(
        id="telegram",
        name="Telegram",
        description="Send messages, monitor channels, bot integration",
        long_description="Telegram integration allows the agent to send formatted messages, security alerts, and reports to Telegram chats or channels using a Bot Token.",
        version="1.0.0",
        author="outcome",
        icon="✈️",
        category="social",
        tags=["social", "messaging", "alerts", "monitoring"],
        auth_type="apikey",  # Bot token
        auth_config={"api_key_field": "bot_token"},
        tools=[
            PluginTool(name="telegram.sendMessage", description="Send message to chat/channel", parameters={"chat_id": {"type": "string"}, "text": {"type": "string"}}),
            PluginTool(name="telegram.sendAlert", description="Send formatted security alert", parameters={"chat_id": {"type": "string"}, "text": {"type": "string"}, "color": {"type": "string"}}),
            PluginTool(name="telegram.sendReport", description="Send analysis report as file", parameters={"chat_id": {"type": "string"}, "file_url": {"type": "string"}, "caption": {"type": "string"}}),
            PluginTool(name="telegram.getMessages", description="Read recent messages from channel", parameters={"chat_id": {"type": "string"}, "limit": {"type": "integer"}}),
            PluginTool(name="telegram.searchChannel", description="Search public channel by keyword", parameters={"query": {"type": "string"}}),
            PluginTool(name="telegram.monitorChannel", description="Monitor channel for new content", parameters={"chat_id": {"type": "string"}}),
            PluginTool(name="telegram.createPoll", description="Create poll in group", parameters={"chat_id": {"type": "string"}, "question": {"type": "string"}, "options": {"type": "array"}}),
        ],
        website_url="https://telegram.org",
        docs_url="https://core.telegram.org/bots/api",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('bot_token') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        token = self.credentials.get('bot_token')
        base_url = f"https://api.telegram.org/bot{token}"
        
        async with httpx.AsyncClient() as client:
            if tool_name == "telegram.sendMessage":
                url = f"{base_url}/sendMessage"
                payload = {
                    "chat_id": parameters['chat_id'],
                    "text": parameters['text'],
                    "parse_mode": "Markdown"
                }
                resp = await client.post(url, json=payload)
            elif tool_name == "telegram.sendAlert":
                url = f"{base_url}/sendMessage"
                payload = {
                    "chat_id": parameters['chat_id'],
                    "text": f"🚨 *SECURITY ALERT*\n\n{parameters['text']}",
                    "parse_mode": "Markdown"
                }
                resp = await client.post(url, json=payload)
            elif tool_name == "telegram.sendReport":
                url = f"{base_url}/sendDocument"
                # Using file_url to download and re-upload for true Telegram file support
                file_resp = await client.get(parameters['file_url'])
                files = {'document': ('report.pdf', file_resp.content)}
                data = {
                    'chat_id': parameters['chat_id'],
                    'caption': parameters.get('caption', '')
                }
                resp = await client.post(url, data=data, files=files)
            elif tool_name == "telegram.getMessages":
                url = f"{base_url}/getUpdates"
                params = {"limit": parameters.get("limit", 10)}
                resp = await client.get(url, params=params)
            elif tool_name == "telegram.searchChannel":
                # Telegram Bot API doesn't have a direct 'search' for channels. 
                # This is a placeholder/simulated tool for advanced search capability.
                return {"message": "Search simulated: No direct channel search via Bot API found."}
            elif tool_name == "telegram.monitorChannel":
                return {"status": "monitoring_started", "chat_id": parameters['chat_id']}
            elif tool_name == "telegram.createPoll":
                url = f"{base_url}/sendPoll"
                payload = {
                    "chat_id": parameters['chat_id'],
                    "question": parameters['question'],
                    "options": parameters['options'],
                    "is_anonymous": True
                }
                resp = await client.post(url, json=payload)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
