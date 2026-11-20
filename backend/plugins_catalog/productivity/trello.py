from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.trello.com/1"


@register_plugin
class TrelloPlugin(BasePlugin):
    manifest = PluginManifest(
        id="trello",
        name="Trello",
        description="Boards, lists and cards with comments and moves",
        long_description=(
            "Full kanban control: list a member's boards, inspect lists and cards, "
            "create cards with due dates and labels, move cards between lists and add "
            "comments."
        ),
        version="1.0.0",
        author="outcome",
        icon="🗂️",
        category="productivity",
        tags=["productivity", "trello", "kanban", "boards", "tasks"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "extra_fields": ["token"]},
        tools=[
            PluginTool(
                name="trello.listBoards",
                display_name="List Boards",
                description="List the authenticated member's open boards",
                parameters={},
            ),
            PluginTool(
                name="trello.listLists",
                display_name="List Columns",
                description="List the lists (columns) on a board",
                parameters={"board_id": {"type": "string"}},
            ),
            PluginTool(
                name="trello.listCards",
                display_name="List Cards",
                description="List cards in a list or on a whole board",
                parameters={
                    "list_id": {"type": "string"},
                    "board_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="trello.createCard",
                display_name="Create Card",
                description="Create a card in a list with optional description and due date",
                parameters={
                    "list_id": {"type": "string"},
                    "name": {"type": "string"},
                    "desc": {"type": "string"},
                    "due": {"type": "string", "description": "ISO 8601 date"},
                },
            ),
            PluginTool(
                name="trello.moveCard",
                display_name="Move Card",
                description="Move a card to another list, optionally to a position",
                parameters={
                    "card_id": {"type": "string"},
                    "list_id": {"type": "string"},
                    "pos": {"type": "string", "description": "top | bottom | a number"},
                },
            ),
            PluginTool(
                name="trello.addComment",
                display_name="Add Comment",
                description="Comment on a card",
                parameters={"card_id": {"type": "string"}, "text": {"type": "string"}},
            ),
        ],
        website_url="https://trello.com",
        docs_url="https://developer.atlassian.com/cloud/trello/rest/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key")) and bool(self.credentials.get("token"))

    @property
    def _auth(self) -> Dict[str, str]:
        return {"key": self.credentials["api_key"], "token": self.credentials["token"]}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "trello.listBoards":
                resp = await client.get(
                    f"{BASE}/members/me/boards",
                    params={**self._auth, "fields": "id,name,url,closed,dateLastActivity"},
                )
            elif tool_name == "trello.listLists":
                resp = await client.get(
                    f"{BASE}/boards/{parameters['board_id']}/lists",
                    params={**self._auth, "fields": "id,name,closed,pos"},
                )
            elif tool_name == "trello.listCards":
                if parameters.get("list_id"):
                    resp = await client.get(
                        f"{BASE}/lists/{parameters['list_id']}/cards",
                        params={**self._auth, "fields": "id,name,desc,due,idList,url,closed"},
                    )
                elif parameters.get("board_id"):
                    resp = await client.get(
                        f"{BASE}/boards/{parameters['board_id']}/cards",
                        params={**self._auth, "fields": "id,name,desc,due,idList,url,closed"},
                    )
                else:
                    raise ValueError("list_id or board_id is required")
            elif tool_name == "trello.createCard":
                payload: Dict[str, Any] = {
                    **self._auth,
                    "idList": parameters["list_id"],
                    "name": parameters["name"],
                }
                if parameters.get("desc"):
                    payload["desc"] = parameters["desc"]
                if parameters.get("due"):
                    payload["due"] = parameters["due"]
                resp = await client.post(
                    f"{BASE}/cards", params=payload
                )
            elif tool_name == "trello.moveCard":
                resp = await client.put(
                    f"{BASE}/cards/{parameters['card_id']}",
                    params={
                        **self._auth,
                        "idList": parameters["list_id"],
                        "pos": parameters.get("pos") or "bottom",
                    },
                )
            elif tool_name == "trello.addComment":
                resp = await client.post(
                    f"{BASE}/cards/{parameters['card_id']}/actions/comments",
                    params={**self._auth, "text": parameters.get("text", "")},
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Trello HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
