"""Browser automation plugin backed by the host's Playwright tool."""

import asyncio
import json
from typing import Any, Dict

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class BrowserAutomationPlugin(BasePlugin):
    manifest = PluginManifest(
        id="browser_automation",
        name="Browser Automation",
        description="Drive a real browser: navigate, click, type, screenshot, extract",
        long_description=(
            "Wraps the platform's Playwright browser tool so the agent can drive a "
            "headless Chromium: navigate to any URL, click buttons, fill forms, "
            "extract page text, take screenshots and download files. Ideal for "
            "pages that need interaction beyond plain HTTP fetches."
        ),
        version="1.0.0",
        author="outcome",
        icon="🌐",
        category="browser",
        tags=["browser", "playwright", "automation", "scraping", "ui"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="browser_automation.navigate",
                display_name="Navigate",
                description="Open a URL and wait for the page to settle",
                parameters={"url": {"type": "string"}},
            ),
            PluginTool(
                name="browser_automation.click",
                display_name="Click",
                description="Click an element matching a CSS selector",
                parameters={"url": {"type": "string"}, "selector": {"type": "string"}},
            ),
            PluginTool(
                name="browser_automation.type",
                display_name="Type",
                description="Fill a text input with the given value",
                parameters={
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "text": {"type": "string"},
                },
            ),
            PluginTool(
                name="browser_automation.content",
                display_name="Page Text",
                description="Extract the visible text content of the current page",
                parameters={"url": {"type": "string"}},
            ),
            PluginTool(
                name="browser_automation.screenshot",
                display_name="Screenshot",
                description="Take a screenshot and return the base64 PNG",
                parameters={"url": {"type": "string"}},
            ),
        ],
        website_url="https://playwright.dev",
        docs_url="https://playwright.dev/python/docs/api/class-page",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def _call(self, action: str, **kwargs) -> Any:
        try:
            from tools import execute_tool
        except Exception as exc:
            raise RuntimeError(f"tool registry unavailable: {exc}")
        result = await execute_tool("Browser", {"action": action, **kwargs})
        return result

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        suffix = tool_name.split(".", 1)[-1]
        url = parameters.get("url", "")
        if suffix == "navigate":
            return await self._call("navigate", url=url)
        if suffix == "click":
            return await self._call("click", url=url, selector=parameters.get("selector", ""))
        if suffix == "type":
            return await self._call(
                "type", url=url, selector=parameters.get("selector", ""), text=parameters.get("text", "")
            )
        if suffix == "content":
            return await self._call("content", url=url)
        if suffix == "screenshot":
            return await self._call("screenshot", url=url)
        raise ValueError(f"Unknown tool: {tool_name}")