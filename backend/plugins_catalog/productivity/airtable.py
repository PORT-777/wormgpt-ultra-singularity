from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.airtable.com/v0"
META = "https://api.airtable.com/v0/meta"


@register_plugin
class AirtablePlugin(BasePlugin):
    manifest = PluginManifest(
        id="airtable",
        name="Airtable",
        description="Query and mutate records in any Airtable base",
        long_description=(
            "Works with personal access tokens: list bases and tables, filter records "
            "with Airtable formula syntax, create/update/delete records and inspect the "
            "schema of a table."
        ),
        version="1.0.0",
        author="outcome",
        icon="🗃️",
        category="productivity",
        tags=["productivity", "airtable", "database", "no-code", "records"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "extra_fields": ["base_id"]},
        tools=[
            PluginTool(
                name="airtable.listBases",
                display_name="List Bases",
                description="List bases this token can access",
                parameters={},
            ),
            PluginTool(
                name="airtable.listTables",
                display_name="List Tables",
                description="List tables and their fields in the configured base",
                parameters={"base_id": {"type": "string"}},
            ),
            PluginTool(
                name="airtable.listRecords",
                display_name="List Records",
                description="List records with optional filterByFormula, sort and view",
                parameters={
                    "table": {"type": "string"},
                    "base_id": {"type": "string"},
                    "filter_by_formula": {"type": "string", "description": "e.g. {Status}='Open'"},
                    "max_records": {"type": "integer", "description": "Default 100"},
                    "view": {"type": "string"},
                },
            ),
            PluginTool(
                name="airtable.getRecord",
                display_name="Get Record",
                description="Fetch a single record by id",
                parameters={"table": {"type": "string"}, "record_id": {"type": "string"}},
            ),
            PluginTool(
                name="airtable.createRecord",
                display_name="Create Record",
                description="Create one record from a fields object",
                parameters={
                    "table": {"type": "string"},
                    "fields": {"type": "object", "description": "Column name to value map"},
                },
            ),
            PluginTool(
                name="airtable.updateRecord",
                display_name="Update Record",
                description="Patch fields on an existing record",
                parameters={
                    "table": {"type": "string"},
                    "record_id": {"type": "string"},
                    "fields": {"type": "object"},
                },
            ),
            PluginTool(
                name="airtable.deleteRecord",
                display_name="Delete Record",
                description="Delete a record by id",
                parameters={"table": {"type": "string"}, "record_id": {"type": "string"}},
            ),
        ],
        website_url="https://airtable.com",
        docs_url="https://airtable.com/developers/web/api/introduction",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['api_key']}",
            "Content-Type": "application/json",
        }

    def _base(self, parameters: Dict[str, Any]) -> str:
        base = parameters.get("base_id") or self.credentials.get("base_id")
        if not base:
            raise ValueError("base_id is required (pass it or store it in credentials)")
        return base

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        async with httpx.AsyncClient(timeout=45.0) as client:
            if tool_name == "airtable.listBases":
                resp = await client.get(f"{META}/bases", headers=headers)
            elif tool_name == "airtable.listTables":
                resp = await client.get(
                    f"{META}/bases/{self._base(parameters)}/tables", headers=headers
                )
            elif tool_name == "airtable.listRecords":
                params: Dict[str, Any] = {
                    "maxRecords": min(int(parameters.get("max_records") or 100), 100)
                }
                if parameters.get("filter_by_formula"):
                    params["filterByFormula"] = parameters["filter_by_formula"]
                if parameters.get("view"):
                    params["view"] = parameters["view"]
                resp = await client.get(
                    f"{BASE}/{self._base(parameters)}/{parameters['table']}",
                    headers=headers,
                    params=params,
                )
            elif tool_name == "airtable.getRecord":
                resp = await client.get(
                    f"{BASE}/{self._base(parameters)}/{parameters['table']}/{parameters['record_id']}",
                    headers=headers,
                )
            elif tool_name == "airtable.createRecord":
                resp = await client.post(
                    f"{BASE}/{self._base(parameters)}/{parameters['table']}",
                    headers=headers,
                    json={"fields": parameters.get("fields") or {}},
                )
            elif tool_name == "airtable.updateRecord":
                resp = await client.patch(
                    f"{BASE}/{self._base(parameters)}/{parameters['table']}/{parameters['record_id']}",
                    headers=headers,
                    json={"fields": parameters.get("fields") or {}},
                )
            elif tool_name == "airtable.deleteRecord":
                resp = await client.delete(
                    f"{BASE}/{self._base(parameters)}/{parameters['table']}/{parameters['record_id']}",
                    headers=headers,
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Airtable HTTP {resp.status_code}: {resp.text[:400]}")
                return {"status": "deleted", "record_id": parameters["record_id"]}
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Airtable HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
