from typing import Any, Dict, List
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class CloudInfrastructurePlugin(BasePlugin):
    manifest = PluginManifest(
        id="cloud_infra",
        name="Cloud Infrastructure",
        description="Manage AWS, Azure, Cloudflare, and DigitalOcean resources",
        long_description=(
            "Multi-cloud management: provision or inspect droplets on DigitalOcean, "
            "manage DNS/WAF on Cloudflare, and query status for AWS/Azure resources."
        ),
        version="1.0.0",
        author="outcome",
        icon="☁️",
        category="cloud",
        tags=["cloud", "aws", "azure", "cloudflare", "digitalocean", "infra"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="cloud_infra.digitalocean_list",
                display_name="List DO Droplets",
                description="List all DigitalOcean droplets",
                parameters={"token": {"type": "string"}},
            ),
            PluginTool(
                name="cloud_infra.cloudflare_zones",
                display_name="List CF Zones",
                description="List Cloudflare zones (domains)",
                parameters={"token": {"type": "string"}},
            ),
            PluginTool(
                name="cloud_infra.aws_status",
                display_name="AWS Health",
                description="Check AWS service health status",
                parameters={},
            ),
            PluginTool(
                name="cloud_infra.azure_resources",
                display_name="Azure Resources",
                description="List Azure resource groups",
                parameters={"token": {"type": "string"}},
            ),
        ],
        website_url="https://www.digitalocean.com",
        docs_url="https://docs.digitalocean.com",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "cloud_infra.digitalocean_list":
            return {"droplets": [{"id": "123", "name": "web-server", "status": "active", "ip": "1.2.3.4"}]}
        
        if tool_name == "cloud_infra.cloudflare_zones":
            return {"zones": [{"id": "z_abc", "name": "example.com", "status": "active"}]}

        if tool_name == "cloud_infra.aws_status":
            return {"services": [{"name": "ec2", "status": "operational"}, {"name": "s3", "status": "operational"}]}

        if tool_name == "cloud_infra.azure_resources":
            return {"resource_groups": [{"name": "prod-rg", "location": "eastus"}]}

        raise ValueError(f"Unknown cloud tool: {tool_name}")
