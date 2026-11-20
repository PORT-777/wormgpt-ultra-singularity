from typing import Any, Dict, List
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class EmailSMTPPlugin(BasePlugin):
    manifest = PluginManifest(
        id="email",
        name="Email (SMTP)",
        description="Send emails and reports from any SMTP server",
        long_description="Drops directly into your mail provider using SMTP. Use it to deliver alerts, scheduled reports, and bulk notifications without depending on a third party API.",
        version="1.0.0",
        author="outcome",
        icon="✉️",
        category="communication",
        tags=["email", "notifications", "reports", "alerts"],
        auth_type="apikey",
        auth_config={
            "api_key_field": "password",
            "host_field": "smtp_host",
            "port_field": "smtp_port",
            "user_field": "smtp_user",
            "from_field": "from_address",
        },
        tools=[
            PluginTool(
                name="email.send",
                display_name="Send Email",
                description="Send a plain email with subject and body",
                parameters={
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
            ),
            PluginTool(
                name="email.sendWithAttachment",
                display_name="Send With Attachment",
                description="Send an email with a file attached (base64 content)",
                parameters={
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "filename": {"type": "string"},
                    "content_b64": {"type": "string"},
                },
            ),
            PluginTool(
                name="email.sendReport",
                display_name="Send Report",
                description="Send a formatted analysis report as HTML email",
                parameters={
                    "to": {"type": "string"},
                    "title": {"type": "string"},
                    "html": {"type": "string"},
                },
            ),
            PluginTool(
                name="email.sendAlert",
                display_name="Send Alert",
                description="Send a high-priority security alert",
                parameters={"to": {"type": "string"}, "summary": {"type": "string"}},
            ),
            PluginTool(
                name="email.sendBulk",
                display_name="Send Bulk",
                description="Send the same email to multiple recipients",
                parameters={
                    "recipients": {"type": "array"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
            ),
        ],
        website_url="https://datatracker.ietf.org/doc/html/rfc5321",
        docs_url="https://datatracker.ietf.org/doc/html/rfc5321",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        required = ["smtp_host", "smtp_port", "smtp_user", "password", "from_address"]
        return all(self.credentials.get(k) for k in required)

    def _send(self, msg: EmailMessage) -> Dict[str, Any]:
        host = self.credentials["smtp_host"]
        port = int(self.credentials["smtp_port"])
        user = self.credentials["smtp_user"]
        password = self.credentials["password"]
        from_addr = self.credentials["from_address"]

        msg["From"] = formataddr(("Cybersec Agent", from_addr))

        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                if self.credentials.get("starttls", True):
                    server.starttls(context=context)
                    server.ehlo()
                server.login(user, password)
                server.send_message(msg)

        return {"status": "sent", "to": msg["To"], "subject": msg["Subject"]}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        # SMTP is blocking; run it in the default executor so the event loop stays healthy.
        import asyncio

        loop = asyncio.get_running_loop()

        def build_and_send() -> Dict[str, Any]:
            msg = EmailMessage()
            msg["Subject"] = parameters.get("subject", "(no subject)")
            msg["To"] = parameters["to"] if "to" in parameters else ", ".join(parameters["recipients"])
            msg.set_content(parameters.get("body", ""))

            if tool_name == "email.sendWithAttachment":
                import base64
                raw = base64.b64decode(parameters["content_b64"])
                msg.add_attachment(
                    raw, maintype="application", subtype="octet-stream", filename=parameters["filename"]
                )
            elif tool_name == "email.sendReport":
                msg.set_content("This report requires an HTML-capable client.")
                msg.add_alternative(
                    f"<h1>{parameters.get('title', 'Report')}</h1>{parameters.get('html', '')}",
                    subtype="html",
                )
            elif tool_name == "email.sendAlert":
                summary = parameters.get("summary", "")
                msg["Subject"] = f"🚨 SECURITY ALERT — {summary[:80]}"
                msg.set_content(f"HIGH PRIORITY ALERT\n\n{summary}")

            return self._send(msg)

        if tool_name not in {
            "email.send",
            "email.sendWithAttachment",
            "email.sendReport",
            "email.sendAlert",
            "email.sendBulk",
        }:
            raise ValueError(f"Unknown tool: {tool_name}")

        return await loop.run_in_executor(None, build_and_send)
