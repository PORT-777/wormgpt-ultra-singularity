from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class SendGridPlugin(BasePlugin):
    manifest = PluginManifest(
        id="sendgrid",
        name="SendGrid",
        description="Transactional email, templates and delivery statistics",
        long_description=(
            "Send HTML or plain-text transactional email, deliver pre-built dynamic "
            "templates with data, list templates, inspect global stats and manage "
            "suppression contacts."
        ),
        version="1.0.0",
        author="outcome",
        icon="✉️",
        category="communication",
        tags=["communication", "email", "sendgrid", "transactional", "templates"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="sendgrid.sendEmail",
                display_name="Send Email",
                description="Send a plain or HTML email to one or more recipients",
                parameters={
                    "to": {"type": "array", "description": "Recipient email addresses"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "is_html": {"type": "boolean", "description": "Default true"},
                    "from_email": {"type": "string", "description": "Defaults to credentials"},
                    "cc": {"type": "array"},
                    "bcc": {"type": "array"},
                },
            ),
            PluginTool(
                name="sendgrid.sendTemplate",
                display_name="Send Template",
                description="Send a dynamic template with handlebars data",
                parameters={
                    "to": {"type": "array"},
                    "template_id": {"type": "string"},
                    "data": {"type": "object"},
                    "from_email": {"type": "string"},
                },
            ),
            PluginTool(
                name="sendgrid.listTemplates",
                display_name="List Templates",
                description="List transactional templates with ids and versions",
                parameters={"generations": {"type": "string", "description": "legacy | dynamic"}},
            ),
            PluginTool(
                name="sendgrid.stats",
                display_name="Stats",
                description="Global email stats (delivered, opens, clicks, bounces)",
                parameters={
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string"},
                    "aggregated_by": {"type": "string", "description": "day | week | month"},
                },
            ),
            PluginTool(
                name="sendgrid.listBounces",
                display_name="Bounces",
                description="List bounced addresses since a timestamp",
                parameters={"start_time": {"type": "integer", "description": "Unix seconds"}},
            ),
        ],
        website_url="https://sendgrid.com",
        docs_url="https://docs.sendgrid.com/api-reference",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['api_key']}",
            "Content-Type": "application/json",
        }

    @property
    def _from(self) -> str:
        return self.credentials.get("from_email") or "noreply@example.com"

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "sendgrid.sendEmail":
                body = parameters.get("body", "")
                content = [
                    {
                        "type": "text/html" if parameters.get("is_html", True) else "text/plain",
                        "value": body,
                    }
                ]
                payload: Dict[str, Any] = {
                    "personalizations": [
                        {
                            "to": [{"email": e} for e in parameters.get("to", [])],
                            **(
                                {"cc": [{"email": e} for e in parameters["cc"]]}
                                if parameters.get("cc")
                                else {}
                            ),
                            **(
                                {"bcc": [{"email": e} for e in parameters["bcc"]]}
                                if parameters.get("bcc")
                                else {}
                            ),
                        }
                    ],
                    "from": {"email": parameters.get("from_email") or self._from},
                    "subject": parameters.get("subject", ""),
                    "content": content,
                }
                resp = await client.post(f"{BASE}/mail/send", headers=headers, json=payload)
                if resp.status_code >= 400:
                    raise RuntimeError(f"SendGrid HTTP {resp.status_code}: {resp.text[:400]}")
                return {"status": "sent", "status_code": resp.status_code}
            elif tool_name == "sendgrid.sendTemplate":
                payload = {
                    "personalizations": [
                        {
                            "to": [{"email": e} for e in parameters.get("to", [])],
                            "dynamic_template_data": parameters.get("data") or {},
                        }
                    ],
                    "from": {"email": parameters.get("from_email") or self._from},
                    "template_id": parameters["template_id"],
                }
                resp = await client.post(f"{BASE}/mail/send", headers=headers, json=payload)
                if resp.status_code >= 400:
                    raise RuntimeError(f"SendGrid HTTP {resp.status_code}: {resp.text[:400]}")
                return {"status": "sent", "status_code": resp.status_code}
            elif tool_name == "sendgrid.listTemplates":
                resp = await client.get(
                    f"{BASE}/templates",
                    headers=headers,
                    params={
                        "generations": parameters.get("generations") or "dynamic",
                        "page_size": 100,
                    },
                )
            elif tool_name == "sendgrid.stats":
                resp = await client.get(
                    f"{BASE}/stats",
                    headers=headers,
                    params={
                        "start_date": parameters["start_date"],
                        "end_date": parameters.get("end_date") or parameters["start_date"],
                        "aggregated_by": parameters.get("aggregated_by") or "day",
                    },
                )
            elif tool_name == "sendgrid.listBounces":
                resp = await client.get(
                    f"{BASE}/suppression/bounces",
                    headers=headers,
                    params={"start_time": int(parameters.get("start_time") or 0), "limit": 100},
                )
            else:
                raise ValueError(f"Unknown sendgrid tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"SendGrid HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
