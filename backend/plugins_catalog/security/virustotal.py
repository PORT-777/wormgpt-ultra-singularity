from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin
import httpx

@register_plugin
class VirusTotalPlugin(BasePlugin):
    manifest = PluginManifest(
        id="virustotal",
        name="VirusTotal",
        description="Analyze files, URLs, IPs and domains for malware",
        long_description="VirusTotal is a service that analyzes files and URLs to detect malware and other malicious content.",
        version="1.0.0",
        author="outcome",
        icon="🛡️",
        category="security",
        tags=["threat-intel", "malware", "ioc", "hash"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="virustotal.lookupHash",
                display_name="Lookup File Hash",
                description="Check if a file hash (MD5/SHA1/SHA256) is malicious",
                parameters={"hash": {"type": "string", "description": "File hash"}},
                requires_auth=True
            ),
            PluginTool(
                name="virustotal.lookupIP",
                display_name="Lookup IP Address",
                description="Get reputation and threat intel for an IP",
                parameters={"ip": {"type": "string"}},
                requires_auth=True
            ),
            PluginTool(
                name="virustotal.lookupDomain",
                display_name="Lookup Domain",
                description="Analyze a domain for malicious activity",
                parameters={"domain": {"type": "string"}},
                requires_auth=True
            ),
            PluginTool(
                name="virustotal.lookupURL",
                display_name="Lookup URL",
                description="Check if a URL is malicious",
                parameters={"url": {"type": "string"}},
                requires_auth=True
            ),
            PluginTool(
                name="virustotal.getReport",
                display_name="Get Full Report",
                description="Get detailed analysis report for any IOC",
                parameters={"ioc": {"type": "string"}, "type": {"type": "string"}},
                requires_auth=True
            ),
        ],
        website_url="https://www.virustotal.com",
        docs_url="https://developers.virustotal.com/reference/",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('api_key') is not None

    async def execute(self, tool_name: str, parameters: dict) -> dict:
        api_key = self.credentials.get('api_key')
        headers = {"x-apikey": api_key}
        
        async with httpx.AsyncClient() as client:
            if tool_name == "virustotal.lookupHash":
                url = f"https://www.virustotal.com/api/v3/files/{parameters['hash']}"
                resp = await client.get(url, headers=headers)
            elif tool_name == "virustotal.lookupIP":
                url = f"https://www.virustotal.com/api/v3/ip_addresses/{parameters['ip']}"
                resp = await client.get(url, headers=headers)
            elif tool_name == "virustotal.lookupDomain":
                url = f"https://www.virustotal.com/api/v3/domains/{parameters['domain']}"
                resp = await client.get(url, headers=headers)
            elif tool_name == "virustotal.lookupURL":
                # URL needs to be base64 encoded for VT API v3
                import base64
                url_encoded = base64.urlsafe_b64encode(parameters['url'].encode()).decode().strip("=")
                url = f"https://www.virustotal.com/api/v3/urls/{url_encoded}"
                resp = await client.get(url, headers=headers)
            elif tool_name == "virustotal.getReport":
                # Generic report lookup - simplified for example
                ioc = parameters['ioc']
                type_ = parameters['type']
                if type_ == "hash":
                    url = f"https://www.virustotal.com/api/v3/files/{ioc}"
                elif type_ == "ip":
                    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ioc}"
                elif type_ == "domain":
                    url = f"https://www.virustotal.com/api/v3/domains/{ioc}"
                else:
                    raise ValueError(f"Unsupported report type: {type_}")
                resp = await client.get(url, headers=headers)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
