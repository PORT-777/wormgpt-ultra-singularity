from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://sheets.googleapis.com/v4/spreadsheets"


@register_plugin
class GoogleSheetsPlugin(BasePlugin):
    manifest = PluginManifest(
        id="google_sheets",
        name="Google Sheets",
        description="Read and write spreadsheets, append rows and create new sheets",
        long_description=(
            "Sheets API v4: read ranges as a 2D array, overwrite or append rows, clear "
            "ranges, read sheet metadata and create brand-new spreadsheets."
        ),
        version="1.0.0",
        author="outcome",
        icon="📊",
        category="productivity",
        tags=["productivity", "google", "sheets", "spreadsheet", "data"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token"},
        tools=[
            PluginTool(
                name="google_sheets.getValues",
                display_name="Read Range",
                description="Read a range such as Sheet1!A1:D20 as a 2D array",
                parameters={
                    "spreadsheet_id": {"type": "string"},
                    "range": {"type": "string"},
                    "value_render": {"type": "string", "description": "FORMATTED_VALUE | UNFORMATTED_VALUE"},
                },
            ),
            PluginTool(
                name="google_sheets.updateValues",
                display_name="Write Range",
                description="Overwrite a range with a 2D array of values",
                parameters={
                    "spreadsheet_id": {"type": "string"},
                    "range": {"type": "string"},
                    "values": {"type": "array", "description": "Array of rows"},
                },
            ),
            PluginTool(
                name="google_sheets.appendValues",
                display_name="Append Rows",
                description="Append rows after the last row of a table",
                parameters={
                    "spreadsheet_id": {"type": "string"},
                    "range": {"type": "string"},
                    "values": {"type": "array"},
                },
            ),
            PluginTool(
                name="google_sheets.clearValues",
                display_name="Clear Range",
                description="Clear all values in a range",
                parameters={"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}},
            ),
            PluginTool(
                name="google_sheets.getSpreadsheet",
                display_name="Spreadsheet Info",
                description="List sheet titles, row/column counts and properties",
                parameters={"spreadsheet_id": {"type": "string"}},
            ),
            PluginTool(
                name="google_sheets.createSpreadsheet",
                display_name="Create Spreadsheet",
                description="Create a new spreadsheet with optional initial sheet names",
                parameters={"title": {"type": "string"}, "sheet_titles": {"type": "array"}},
            ),
        ],
        website_url="https://sheets.google.com",
        docs_url="https://developers.google.com/sheets/api/reference/rest",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "google_sheets.getValues":
                resp = await client.get(
                    f"{BASE}/{parameters['spreadsheet_id']}/values/{parameters['range']}",
                    headers=headers,
                    params={
                        "valueRenderOption": parameters.get("value_render") or "FORMATTED_VALUE"
                    },
                )
            elif tool_name == "google_sheets.updateValues":
                resp = await client.put(
                    f"{BASE}/{parameters['spreadsheet_id']}/values/{parameters['range']}",
                    headers=headers,
                    params={"valueInputOption": "USER_ENTERED"},
                    json={"values": parameters.get("values") or []},
                )
            elif tool_name == "google_sheets.appendValues":
                resp = await client.post(
                    f"{BASE}/{parameters['spreadsheet_id']}/values/{parameters['range']}:append",
                    headers=headers,
                    params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
                    json={"values": parameters.get("values") or []},
                )
            elif tool_name == "google_sheets.clearValues":
                resp = await client.post(
                    f"{BASE}/{parameters['spreadsheet_id']}/values/{parameters['range']}:clear",
                    headers=headers,
                    json={},
                )
            elif tool_name == "google_sheets.getSpreadsheet":
                resp = await client.get(
                    f"{BASE}/{parameters['spreadsheet_id']}",
                    headers=headers,
                    params={"fields": "spreadsheetId,properties,sheets.properties"},
                )
            elif tool_name == "google_sheets.createSpreadsheet":
                body: Dict[str, Any] = {"properties": {"title": parameters["title"]}}
                titles = parameters.get("sheet_titles") or []
                if titles:
                    body["sheets"] = [
                        {"properties": {"title": t}} for t in titles
                    ]
                resp = await client.post(
                    BASE,
                    headers=headers,
                    params={"fields": "spreadsheetId,spreadsheetUrl,sheets.properties"},
                    json=body,
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Sheets HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
