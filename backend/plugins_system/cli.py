import os
import argparse
import sys
from datetime import datetime

class PluginScaffolder:
    """
    A CLI tool to scaffold new plugins based on the established SDK.
    """
    def __init__(self, base_path: str = "backend/plugins_catalog"):
        self.base_path = base_path
        self.categories = ["security", "social", "productivity", "communication", "devops", "cloud", "siem", "custom"]

    def create_plugin(self, name: str, category: str, plugin_id: str):
        if category not in self.categories:
            print(f"Error: Invalid category. Choose from: {', '.join(self.categories)}")
            return

        # Ensure category directory exists
        category_dir = os.path.join(self.base_path, category)
        os.makedirs(category_dir, exist_ok=True)

        plugin_dir = os.path.join(category_dir, plugin_id)
        if os.path.exists(plugin_dir):
            print(f"Error: Plugin directory '{plugin_id}' already exists.")
            return

        os.makedirs(plugin_dir)

        # Define template content
        template_content = f'''"""
{name} Plugin Implementation
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin
import httpx

@register_plugin
class {self._to_pascal_case(name)}Plugin(BasePlugin):
    manifest = PluginManifest(
        id="{plugin_id}",
        name="{name}",
        description="Description for {name}",
        long_description="Detailed description of what {name} does.",
        version="1.0.0",
        author="User",
        icon="🛠️",
        category="{category}",
        tags=["custom"],
        auth_type="apikey",
        auth_config={{"api_key_field": "api_key"}},
        tools=[
            PluginTool(
                name="{plugin_id}.action",
                display_name="Example Action",
                description="Description of the action",
                parameters={{"input": {{"type": "string"}}}},
                requires_auth=True
            ),
        ],
        website_url="https://example.com",
        docs_url="https://docs.example.com",
        is_free=True,
        is_official=False
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('api_key') is not None

    async def execute(self, tool_name: str, parameters: dict) -> dict:
        api_key = self.credentials.get('api_key')
        
        async with httpx.AsyncClient() as client:
            if tool_name == "{plugin_id}.action":
                # Implement actual logic here
                return {{"status": "success", "message": f"Action executed with {{parameters.get('input')}}"}}
            else:
                raise ValueError(f"Unknown tool: {{tool_name}}")
'''

        file_path = os.path.join(plugin_dir, f"{plugin_id}.py")
        with open(file_path, "w") as f:
            f.write(template_content)

        print(f"Successfully scaffolded {name} plugin at: {file_path}")
        print(f"Next steps: 1. Edit {file_path} to implement logic. 2. Register in registry.py if needed.")

    def _to_pascal_case(self, text: str) -> str:
        return "".join(x.capitalize() for x in text.replace("_", " ").replace("-", " ").split())

def main():
    parser = argparse.ArgumentParser(description="Cybersec Agent Plugin Scaffolder")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Create a new plugin")
    create_parser.add_argument("name", help="Human readable name of the plugin (e.g. 'My Cool Plugin')")
    create_parser.add_argument("--id", required=True, help="Machine readable ID (e.g. 'my_cool_plugin')")
    create_parser.add_argument("--category", default="custom", help="Plugin category")

    args = parser.parse_args()

    scaffolder = PluginScaffolder()

    if args.command == "create":
        scaffolder.create_plugin(args.name, args.category, args.id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
