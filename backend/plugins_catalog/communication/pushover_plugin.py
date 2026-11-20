from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class PushoverPlugin(BasePlugin):
    manifest = PluginManifest(
        id="pushover",
        name="Pushover",
        description="Instant push notifications to phones and desktops",
        long_description=(
            "Deliver alerts to any Pushover client with priority, sound, title, URL and "
            "attachment support, check remaining message quota and validate user keys."
        ),
        version="1.0.0",
        author="outcome",
        icon="🔔",
        category="communication",
        tags=["communication", "pushover", "notifications", "alerts", "mobile"],
        auth_type="apikey",
        auth_config={"api_key_field": "token", "extra_fields": ["user"]},
        tools=[
            PluginTool(
                name="pushover.send",
                display_name="Send Notification",
                description="Push a message with optional title, priority and URL",
                parameters={
                    "message": {"type": "string"},
                    "title": {"type": "string"},
                    "priority": {"type": "integer", "description": "-2 to 2 (2 = emergency)"},
                    "sound": {"type": "string", "description": "pushover | bike | siren | none"},
                    "url": {"type": "string"},
                    "device": {"type": "string"},
                },
            ),
            PluginTool(
                name="pushover.validate",
                display_name="Validate User",
                description="Validate the stored user key and device",
                parameters={"device": {"type": "string"}},
            ),
            PluginTool(
                name="pushover.limits",
                display_name="Quota",
                description="Read the monthly message limit and remaining quota",
                parameters={},
            ),
        ],
        website_url="https://pushover.net",
        docs_url="https://pushover.net/api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("token")) and bool(self.credentials.get("user"))

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        auth = {
            "token": self.credentials["token"],
            "user": self.credentials["user"],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "pushover.send":
                payload: Dict[str, Any] = {
                    **auth,
                    "message": parameters["message"],
                }
                for key in ("title", "sound", "url", "device"):
                    if parameters.get(key):
                        payload[key] = parameters[key]
                if parameters.get("priority") is not None:
                    payload["priority"] = int(parameters["priority"])
                resp = await client.post(f"https://api.pushover.net/1/messages.json", data=payload)
            elif tool_name == "pushover.validate":
                resp = await client.post(
                    f"https://api.pushover.net/1/users/validate.json",
                    data={**auth, **({"device": parameters["device"]} if parameters.get("device") else {})},
                )
            elif tool_name == "pushover.limits":
                resp = await client.get(f"https://api.pushover.net/1/limits.json", params=auth)
            else:
                raise ValueError(f"Unknown pushover tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Pushover HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
