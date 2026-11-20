from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class CustomUniversalPlugin(BasePlugin):
    manifest = PluginManifest(
        id="universal_tools",
        name="Universal Toolbox",
        description="General purpose automation: URL fetching, data parsing, and system utils",
        long_description=(
            "A collection of highly versatile utility tools: fetch content from URLs, "
            "convert data formats, parse structured strings, and perform basic "
            "system-level command automation."
        ),
        version="1.0.0",
        author="outcome",
        icon="🛠️",
        category="custom",
        tags=["utils", "automation", "general"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="universal_tools.fetch_url",
                display_name="HTTP Fetch",
                description="Fetch content from a URL (raw text/html)",
                parameters={
                    "url": {"type": "string"},
                    "headers": {"type": "object", "description": "Custom headers dictionary"},
                },
            ),
            PluginTool(
                name="universal_tools.parse_json",
                display_name="JSON Parse",
                description="Safely parse a JSON string into a dictionary",
                parameters={"json_string": {"type": "string"}},
            ),
            PluginTool(
                name="universal_tools.run_shell",
                display_name="Shell Execute",
                description="Run a local shell command (highly restricted)",
                parameters={"command": {"type": "string"}},
            ),
        ],
        website_url="https://github.com",
        docs_url="https://github.com",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        import json
        import subprocess

        if tool_name == "universal_tools.fetch_url":
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(parameters["url"], headers=parameters.get("headers"))
                return {"status": resp.status_code, "content": resp.text[:10000]}

        if tool_name == "universal_tools.parse_json":
            try:
                return json.loads(parameters["json_string"])
            except Exception as e:
                return {"error": str(e)}

        if tool_name == "universal_tools.run_shell":
            try:
                result = subprocess.run(
                    parameters["command"], 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
            except Exception as e:
                return {"error": str(e)}

        raise ValueError(f"Unknown universal tool: {tool_name}")
