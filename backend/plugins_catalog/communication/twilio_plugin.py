from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class TwilioPlugin(BasePlugin):
    manifest = PluginManifest(
        id="twilio",
        name="Twilio",
        description="Send SMS, WhatsApp messages and place voice calls",
        long_description=(
            "Programmable messaging and voice: send SMS or WhatsApp messages, list "
            "recent messages with delivery status, and trigger outbound voice calls "
            "with TwiML."
        ),
        version="1.0.0",
        author="outcome",
        icon="📞",
        category="communication",
        tags=["communication", "twilio", "sms", "voice", "whatsapp"],
        auth_type="apikey",
        auth_config={"api_key_field": "auth_token", "extra_fields": ["account_sid", "from_number"]},
        tools=[
            PluginTool(
                name="twilio.sendSms",
                display_name="Send SMS",
                description="Send an SMS from the configured number",
                parameters={"to": {"type": "string", "description": "E.164 number"}, "body": {"type": "string"}},
            ),
            PluginTool(
                name="twilio.sendWhatsApp",
                display_name="Send WhatsApp",
                description="Send a WhatsApp message through the Twilio sandbox or sender",
                parameters={
                    "to": {"type": "string"},
                    "body": {"type": "string"},
                    "from_number": {"type": "string", "description": "Default whatsapp:+14155238886"},
                },
            ),
            PluginTool(
                name="twilio.listMessages",
                display_name="List Messages",
                description="List recent messages with status, direction and price",
                parameters={"limit": {"type": "integer", "description": "Default 20, max 1000"}},
            ),
            PluginTool(
                name="twilio.makeCall",
                display_name="Make Call",
                description="Place an outbound call that reads a message with TwiML",
                parameters={
                    "to": {"type": "string"},
                    "message": {"type": "string", "description": "Text spoken with <Say>"},
                },
            ),
        ],
        website_url="https://www.twilio.com",
        docs_url="https://www.twilio.com/docs/usage/api",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("account_sid")) and bool(
            self.credentials.get("auth_token")
        )

    @property
    def _base(self) -> str:
        return f"https://api.twilio.com/2010-04-01/Accounts/{self.credentials['account_sid']}"

    @property
    def _auth(self) -> tuple:
        return (self.credentials["account_sid"], self.credentials["auth_token"])

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0, auth=self._auth) as client:
            if tool_name == "twilio.sendSms":
                resp = await client.post(
                    f"{self._base}/Messages.json",
                    data={
                        "To": parameters["to"],
                        "From": self.credentials.get("from_number", ""),
                        "Body": parameters.get("body", ""),
                    },
                )
            elif tool_name == "twilio.sendWhatsApp":
                sender = parameters.get("from_number") or self.credentials.get(
                    "whatsapp_from", "whatsapp:+14155238886"
                )
                resp = await client.post(
                    f"{self._base}/Messages.json",
                    data={
                        "To": f"whatsapp:{parameters['to']}" if not parameters["to"].startswith("whatsapp:") else parameters["to"],
                        "From": sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}",
                        "Body": parameters.get("body", ""),
                    },
                )
            elif tool_name == "twilio.listMessages":
                resp = await client.get(
                    f"{self._base}/Messages.json",
                    params={"PageSize": min(int(parameters.get("limit") or 20), 1000)},
                )
            elif tool_name == "twilio.makeCall":
                twiml = (
                    "<Response><Say voice=\"alice\">"
                    + parameters.get("message", "")
                    + "</Say></Response>"
                )
                resp = await client.post(
                    f"{self._base}/Calls.json",
                    data={
                        "To": parameters["to"],
                        "From": self.credentials.get("from_number", ""),
                        "Twiml": twiml,
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Twilio HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
