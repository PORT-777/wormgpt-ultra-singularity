from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class URLhausPlugin(BasePlugin):
    manifest = PluginManifest(
        id="urlhaus",
        name="URLhaus",
        description="Malicious URL database by abuse.ch",
        long_description="URLhaus tracks URLs used for malware distribution. Use it to check if a URL is actively serving malware, or to report a new malicious URL.",
        version="1.0.0",
        author="outcome",
        icon="🔗",
        category="security",
        tags=["malware", "urls", "phishing", "distribution"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="urlhaus.lookupURL",
                display_name="Lookup URL",
                description="Check if a URL is a known malware distribution point",
                parameters={"url": {"type": "string"}},
                requires_auth=False,
            ),
            PluginTool(
                name="urlhaus.lookupHost",
                display_name="Lookup Host",
                description="Check if a domain or IP hosts known malicious URLs",
                parameters={"host": {"type": "string"}},
                requires_auth=False,
            ),
            PluginTool(
                name="urlhaus.submitURL",
                display_name="Submit URL",
                description="Report a malicious URL to URLhaus",
                parameters={"url": {"type": "string"}, "tags": {"type": "string"}},
                requires_auth=False,
            ),
        ],
        website_url="https://urlhaus.abuse.ch",
        docs_url="https://urlhaus.abuse.ch/api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "urlhaus.lookupURL":
                data = {"url": parameters["url"]}
            elif tool_name == "urlhaus.lookupHost":
                data = {"host": parameters["host"]}
            elif tool_name == "urlhaus.submitURL":
                data = {"url": parameters["url"]}
                if parameters.get("tags"):
                    data["tags"] = parameters["tags"]
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp = await client.post("https://urlhaus-api.abuse.ch/v1/", data=data)
            resp.raise_for_status()
            return resp.json()
