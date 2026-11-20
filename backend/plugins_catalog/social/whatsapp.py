from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://graph.facebook.com/v21.0"


@register_plugin
class WhatsAppPlugin(BasePlugin):
    manifest = PluginManifest(
        id="whatsapp",
        name="WhatsApp Cloud",
        description="Send WhatsApp messages, templates and media from a business number",
        long_description=(
            "WhatsApp Business Cloud API: send free-form text inside the 24h window, "
            "deliver approved templates, push images/documents, mark messages as read "
            "and inspect the business profile."
        ),
        version="1.0.0",
        author="outcome",
        icon="💬",
        category="social",
        tags=["social", "whatsapp", "messaging", "meta", "business"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token", "user_id_field": "phone_number_id"},
        tools=[
            PluginTool(
                name="whatsapp.sendText",
                display_name="Send Text",
                description="Send a text message to a phone number in E.164 format",
                parameters={
                    "to": {"type": "string", "description": "e.g. 447700900123"},
                    "text": {"type": "string"},
                    "preview_url": {"type": "boolean"},
                },
            ),
            PluginTool(
                name="whatsapp.sendTemplate",
                display_name="Send Template",
                description="Send an approved template message with up to 3 body variables",
                parameters={
                    "to": {"type": "string"},
                    "template": {"type": "string", "description": "Template name"},
                    "language": {"type": "string", "description": "Default en_US"},
                    "variables": {"type": "array", "description": "Body parameter values"},
                },
            ),
            PluginTool(
                name="whatsapp.sendMedia",
                display_name="Send Media",
                description="Send an image, document, audio or video by public URL",
                parameters={
                    "to": {"type": "string"},
                    "media_type": {"type": "string", "description": "image | document | audio | video"},
                    "url": {"type": "string"},
                    "caption": {"type": "string"},
                },
            ),
            PluginTool(
                name="whatsapp.markRead",
                display_name="Mark Read",
                description="Mark an incoming message id as read (shows blue ticks)",
                parameters={"message_id": {"type": "string"}},
            ),
            PluginTool(
                name="whatsapp.businessProfile",
                display_name="Business Profile",
                description="Read the verified name, description and vertical of the number",
                parameters={},
            ),
        ],
        website_url="https://business.whatsapp.com",
        docs_url="https://developers.facebook.com/docs/whatsapp/cloud-api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token")) and bool(
            self.credentials.get("phone_number_id")
        )

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    @property
    def _phone(self) -> str:
        return self.credentials["phone_number_id"]

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "whatsapp.sendText":
                resp = await client.post(
                    f"{BASE}/{self._phone}/messages",
                    headers=self._headers,
                    json={
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": parameters["to"],
                        "type": "text",
                        "text": {
                            "preview_url": bool(parameters.get("preview_url")),
                            "body": parameters.get("text", ""),
                        },
                    },
                )
            elif tool_name == "whatsapp.sendTemplate":
                variables = parameters.get("variables") or []
                template: Dict[str, Any] = {
                    "name": parameters["template"],
                    "language": {"code": parameters.get("language") or "en_US"},
                }
                if variables:
                    template["components"] = [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": str(v)} for v in variables],
                        }
                    ]
                resp = await client.post(
                    f"{BASE}/{self._phone}/messages",
                    headers=self._headers,
                    json={
                        "messaging_product": "whatsapp",
                        "to": parameters["to"],
                        "type": "template",
                        "template": template,
                    },
                )
            elif tool_name == "whatsapp.sendMedia":
                media_type = parameters.get("media_type") or "image"
                resp = await client.post(
                    f"{BASE}/{self._phone}/messages",
                    headers=self._headers,
                    json={
                        "messaging_product": "whatsapp",
                        "to": parameters["to"],
                        "type": media_type,
                        media_type: {
                            "link": parameters["url"],
                            "caption": parameters.get("caption", ""),
                        },
                    },
                )
            elif tool_name == "whatsapp.markRead":
                resp = await client.post(
                    f"{BASE}/{self._phone}/messages",
                    headers=self._headers,
                    json={
                        "messaging_product": "whatsapp",
                        "status": "read",
                        "message_id": parameters["message_id"],
                    },
                )
            elif tool_name == "whatsapp.businessProfile":
                resp = await client.get(
                    f"{BASE}/{self._phone}/whatsapp_business_profile",
                    headers=self._headers,
                    params={"fields": "verified_name,display_phone_number,description,vertical,websites"},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"WhatsApp HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
