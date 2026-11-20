import json
from typing import Any, Dict

import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

API = "https://api.monday.com/v2"


@register_plugin
class MondayPlugin(BasePlugin):
    manifest = PluginManifest(
        id="monday",
        name="Monday.com",
        description="Manage Monday.com boards, items and updates",
        long_description=(
            "Monday.com GraphQL API with an OAuth access token: list boards and "
            "items, create and update items with column values, and post updates "
            "to an item."
        ),
        version="1.0.0",
        author="outcome",
        icon="🟣",
        category="productivity",
        tags=["productivity", "monday", "boards", "items", "pm"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="monday.listBoards",
                description="List boards",
                parameters={"limit": {"type": "integer"}},
            ),
            PluginTool(
                name="monday.listItems",
                description="List items on a board",
                parameters={"board_id": {"type": "string"}},
            ),
            PluginTool(
                name="monday.createItem",
                description="Create an item on a board",
                parameters={
                    "board_id": {"type": "string"},
                    "item_name": {"type": "string"},
                    "column_values": {"type": "object"},
                },
            ),
            PluginTool(
                name="monday.updateItem",
                description="Update an item's column values",
                parameters={
                    "board_id": {"type": "string"},
                    "item_id": {"type": "string"},
                    "column_values": {"type": "object"},
                },
            ),
            PluginTool(
                name="monday.createUpdate",
                description="Post an update to an item",
                parameters={
                    "item_id": {"type": "string"},
                    "body": {"type": "string"},
                },
            ),
        ],
        website_url="https://monday.com",
        docs_url="https://developer.monday.com/api-reference/docs",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        # Monday expects the raw token in the Authorization header.
        return {
            "Authorization": str(self.credentials["access_token"]),
            "Content-Type": "application/json",
        }

    async def _gql(self, client: httpx.AsyncClient, query: str, variables: Dict[str, Any]) -> Any:
        resp = await client.post(
            API, headers=self._headers, json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        payload = resp.json() or {}
        if payload.get("errors"):
            raise RuntimeError(f"Monday GraphQL error: {payload['errors']}")
        return payload.get("data")

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "monday.listBoards":
                query = "query ($limit: Int) { boards(limit: $limit) { id name state } }"
                return await self._gql(
                    client, query, {"limit": min(int(parameters.get("limit") or 25), 100)}
                )
            if tool_name == "monday.listItems":
                query = (
                    "query ($ids: [ID!]) { boards(ids: $ids) "
                    "{ items_page(limit: 50) { items { id name } } } }"
                )
                return await self._gql(
                    client, query, {"ids": [str(parameters["board_id"])]}
                )
            if tool_name == "monday.createItem":
                query = (
                    "mutation ($board: ID!, $name: String!, $cols: JSON) "
                    "{ create_item(board_id: $board, item_name: $name, column_values: $cols) "
                    "{ id } }"
                )
                return await self._gql(
                    client,
                    query,
                    {
                        "board": str(parameters["board_id"]),
                        "name": parameters["item_name"],
                        "cols": json.dumps(parameters.get("column_values") or {}),
                    },
                )
            if tool_name == "monday.updateItem":
                query = (
                    "mutation ($board: ID!, $item: ID!, $cols: JSON) "
                    "{ change_multiple_column_values(board_id: $board, item_id: $item, "
                    "column_values: $cols) { id } }"
                )
                return await self._gql(
                    client,
                    query,
                    {
                        "board": str(parameters["board_id"]),
                        "item": str(parameters["item_id"]),
                        "cols": json.dumps(parameters.get("column_values") or {}),
                    },
                )
            if tool_name == "monday.createUpdate":
                query = (
                    "mutation ($item: ID!, $body: String!) "
                    "{ create_update(item_id: $item, body: $body) { id } }"
                )
                return await self._gql(
                    client,
                    query,
                    {"item": str(parameters["item_id"]), "body": parameters["body"]},
                )
            raise ValueError(f"Unknown tool: {tool_name}")
