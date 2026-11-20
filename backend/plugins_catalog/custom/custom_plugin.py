from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
import httpx

class CustomPluginTemplate(BasePlugin):
    """
    Template for creating custom plugins.
    Users can inherit from this class to build their own integrations.
    """

    manifest = PluginManifest(
        id="template_plugin",
        name="Custom Plugin Template",
        description="A template for building your own custom plugins.",
        long_description="Follow this structure to create your own plugin. Replace the manifest and the execute method with your specific logic.",
        version="1.0.0",
        author="User",
        icon="🛠️",
        category="custom",
        tags=["template", "custom"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="custom.action",
                display_name="Custom Action",
                description="An example action for your custom plugin",
                parameters={"input": {"type": "string"}},
                requires_auth=True
            ),
        ],
        website_url="https://example.com",
        docs_url="https://example.com/docs",
        is_free=True,
        is_official=False
    )

    def _validate_credentials(self) -> bool:
        """Verify that the provided credentials meet the plugin's requirements."""
        return self.credentials.get('api_key') is not None

    async def execute(self, tool_name: str, parameters: dict) -> dict:
        """
        Execute the requested tool action.
        """
        api_key = self.credentials.get('api_key')
        
        async with httpx.AsyncClient() as client:
            if tool_name == "custom.action":
                # Example of a generic HTTP request
                url = "https://api.example.com/action"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {"data": parameters.get("input")}
                
                # For demonstration, we'll just return a success message 
                # instead of actually making a call to a non-existent URL.
                # In a real plugin, you would uncomment the line below:
                # resp = await client.post(url, json=payload, headers=headers)
                # resp.raise_for_status()
                # return resp.json()
                
                return {"status": "success", "message": f"Custom action called with: {parameters.get('input')}"}
            
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
