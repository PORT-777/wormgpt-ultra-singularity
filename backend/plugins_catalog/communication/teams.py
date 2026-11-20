from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class TeamsPlugin(BasePlugin):
    manifest = PluginManifest(
        id="teams",
        name="Microsoft Teams",
        description="Send messages and alerts to Teams channels",
        long_description="Post to Teams via incoming webhooks or a Bot Framework token. Supports plain messages, adaptive cards, and rich security alerts.",
        version="1.0.0",
        author="outcome",
        icon="🟪",
        category="communication",
        tags=["team", "alerts", "microsoft", "enterprise"],
        auth_type="webhook",
        auth_config={"webhook_url_field": "webhook_url"},
        tools=[
            PluginTool(
                name="teams.sendMessage",
                display_name="Send Message",
                description="Send a plain text message to a Teams channel",
                parameters={"text": {"type": "string"}},
            ),
            PluginTool(
                name="teams.sendAdaptiveCard",
                display_name="Send Adaptive Card",
                description="Send a rich Adaptive Card payload to Teams",
                parameters={"card": {"type": "object"}},
            ),
            PluginTool(
                name="teams.sendAlert",
                display_name="Send Security Alert",
                description="Send a formatted security alert with severity color",
                parameters={
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "severity": {"type": "string", "description": "low | medium | high | critical"},
                },
            ),
            PluginTool(
                name="teams.createMeeting",
                display_name="Create Meeting",
                description="Schedule a Teams meeting via Microsoft Graph",
                parameters={
                    "subject": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "attendees": {"type": "array"},
                },
            ),
            PluginTool(
                name="teams.uploadFile",
                display_name="Upload File",
                description="Upload a file to the channel's Files tab",
                parameters={"filename": {"type": "string"}, "content_b64": {"type": "string"}},
            ),
        ],
        website_url="https://www.microsoft.com/microsoft-teams",
        docs_url="https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/connectors-using",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("webhook_url"))

    @property
    def _severity_color(self) -> Dict[str, str]:
        return {
            "low": "Good",
            "medium": "Warning",
            "high": "Attention",
            "critical": "Attention",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "teams.sendMessage":
            payload = {"text": parameters["text"]}

        elif tool_name == "teams.sendAdaptiveCard":
            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": parameters["card"],
                    }
                ],
            }

        elif tool_name == "teams.sendAlert":
            severity = parameters.get("severity", "high")
            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "size": "Large",
                                    "weight": "Bolder",
                                    "text": f"🚨 {parameters.get('title', 'Security Alert')}",
                                    "color": self._severity_color.get(severity, "Attention"),
                                },
                                {
                                    "type": "TextBlock",
                                    "text": parameters.get("summary", ""),
                                    "wrap": True,
                                },
                            ],
                            "msteams": {"width": "Full"},
                        },
                    }
                ],
            }
        elif tool_name in {"teams.createMeeting", "teams.uploadFile"}:
            # Those require Graph API tokens, not just webhooks.
            raise NotImplementedError(
                "This action requires a Microsoft Graph token, not a webhook. Configure OAuth2 to enable it."
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(self.credentials["webhook_url"], json=payload)
            resp.raise_for_status()
            return {"status": "sent"}
