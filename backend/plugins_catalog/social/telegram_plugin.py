from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.telegram.org"


@register_plugin
class TelegramPlugin(BasePlugin):
    manifest = PluginManifest(
        id="telegram",
        name="Telegram Bot",
        description="Send messages, manage chats and groups via Telegram Bot API",
        long_description=(
            "Full Telegram Bot integration: send text, media, and location messages; "
            "manage chat members, create groups, and get updates/messages using a Bot Token."
        ),
        version="1.0.0",
        author="outcome",
        icon="🔵",
        category="social",
        tags=["social", "telegram", "bot", "messaging"],
        auth_type="apikey",
        auth_config={"api_key_field": "bot_token"},
        tools=[
            PluginTool(
                name="telegram.sendMessage",
                display_name="Send Message",
                description="Send a text message to a chat (user, group, or channel) by ID",
                parameters={
                    "chat_id": {"type": "string", "description": "e.g. 12345678 or @username"},
                    "text": {"type": "string"},
                    "parse_mode": {"type": "string", "description": "MarkdownV2 | HTML"},
                },
            ),
            PluginTool(
                name="telegram.sendPhoto",
                display_name="Send Photo",
                description="Send a photo to a chat via URL",
                parameters={
                    "chat_id": {"type": "string"},
                    "photo_url": {"type": "string"},
                    "caption": {"type": "string"},
                },
            ),
            PluginTool(
                name="telegram.getUpdates",
                display_name="Get Updates",
                description="Fetch recent unconfirmed updates (messages, edits, etc.)",
                parameters={"offset": {"type": "integer", "description": "Last seen update_id + 1"}},
            ),
            PluginTool(
                name="telegram.getChat",
                display_name="Get Chat Info",
                description="Get metadata for a specific chat or user",
                parameters={"chat_id": {"type": "string"}},
            ),
        ],
        website_url="https://telegram.org",
        docs_url="https://core.telegram.org/bots/api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("bot_token"))

    @property
    def _base(self) -> str:
        return f"{BASE}/{self.credentials['bot_token']}"

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "telegram.sendMessage":
                resp = await client.post(
                    f"{self._base}/sendMessage",
                    json={
                        "chat_id": parameters["chat_id"],
                        "text": parameters["text"],
                        "parse_mode": parameters.get("parse_mode", "HTML"),
                    },
                )
            elif tool_name == "telegram.sendPhoto":
                resp = await client.post(
                    f"{self._base}/sendPhoto",
                    json={
                        "chat_id": parameters["chat_id"],
                        "photo": parameters["photo_url"],
                        "caption": parameters.get("caption", ""),
                    },
                )
            elif tool_name == "telegram.getUpdates":
                resp = await client.get(
                    f"{self._base}/getUpdates",
                    params={"offset": parameters.get("offset")},
                )
            elif tool_name == "telegram.getChat":
                resp = await client.get(
                    f"{self._base}/getChat",
                    params={"chat_id": parameters["chat_id"]},
                )
            else:
                raise ValueError(f"Unknown telegram tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Telegram HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
